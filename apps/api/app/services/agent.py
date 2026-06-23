"""Mağaza AI Asistanı — araçlı (tool-use) ajan.

LLM'e mağaza verisine erişen ve aksiyon alan araçlar verilir (OpenAI-uyumlu tool-calling):
  okuma: KPI, SKU kârlılık, müşteri, huni, reklam, fiyat, aksiyon kuyruğu, simülasyon
  yazma: execute_action (kampanya kapat / fiyat değiştir / stok sipariş et)
Anahtar yoksa deterministik niyet-yönlendirici (fallback) aynı araçları kullanır.
"""
import json
import re

from sqlalchemy.orm import Session

from app.services import llm
from app.services.action_queue import build_queue
from app.services.ad_engine import campaign_metrics
from app.services.customer_analytics import customer_overview
from app.services.decision_score import decision_scores
from app.services.elasticity import pricing_recommendations, simulate_one
from app.services.executor import execute as exec_action
from app.services.funnel import funnel_analysis
from app.services.kpi_engine import kpi_summary

SYSTEM = (
    "Sen Commerce-AI mağaza asistanısın. Kullanıcının e-ticaret verisine SADECE verilen "
    "araçlarla eriş; asla veri uydurma. Türkçe, kısa ve net yanıtla, sayıları yorumla. "
    "Aksiyon araçlarını (execute_action) kullanmadan önce ne yapacağını bir cümleyle belirt, "
    "sonra uygula ve sonucu (before→after) söyle. Para birimi ₺."
)

TOOLS = [
    {"name": "get_kpi", "description": "Son 30 gün KPI özeti: ciro, sipariş, AOV, dönüşüm, ROAS, reklam.",
     "input_schema": {"type": "object", "properties": {}}},
    {"name": "get_sku_profitability",
     "description": "SKU bazında kârlılık + karar skoru (zararlı/yıldız ürünler, stok riski).",
     "input_schema": {"type": "object", "properties": {}}},
    {"name": "get_customers", "description": "Müşteri özeti: LTV, tekrar oranı, terk %, segmentler.",
     "input_schema": {"type": "object", "properties": {}}},
    {"name": "get_funnel", "description": "Trafik/dönüşüm hunisi ve darboğaz.",
     "input_schema": {"type": "object", "properties": {}}},
    {"name": "get_ads", "description": "Reklam kampanyaları: ROAS, CAC, kapatılması gerekenler.",
     "input_schema": {"type": "object", "properties": {}}},
    {"name": "get_pricing", "description": "SKU fiyat elastikiyeti ve önerilen fiyat hamleleri.",
     "input_schema": {"type": "object", "properties": {}}},
    {"name": "get_action_queue", "description": "Paraya göre sıralı yapılacaklar listesi (tüm domainler).",
     "input_schema": {"type": "object", "properties": {}}},
    {"name": "simulate_price",
     "description": "Bir SKU'da %değişimin satış ve kâra etkisini simüle eder.",
     "input_schema": {"type": "object", "properties": {
         "sku": {"type": "string"}, "pct": {"type": "number", "description": "+zam / -indirim"}},
         "required": ["sku", "pct"]}},
    {"name": "execute_action",
     "description": "AKSİYON UYGULA. type='cut_campaign' (target=kampanya id), "
                    "'adjust_price' (target=sku, params.pct), 'reorder_stock' (target=sku, params.qty).",
     "input_schema": {"type": "object", "properties": {
         "type": {"type": "string", "enum": ["cut_campaign", "adjust_price", "reorder_stock"]},
         "target": {"type": "string"},
         "params": {"type": "object"}}, "required": ["type", "target"]}},
]


def run_tool(db: Session, org_id: int, name: str, args: dict) -> dict:
    if name == "get_kpi":
        return kpi_summary(db, org_id)
    if name == "get_sku_profitability":
        d = decision_scores(db, org_id)
        return {"summary": d["summary"],
                "items": [{k: it[k] for k in ("sku", "category", "units", "profit", "margin", "decision_score", "recommendation")}
                          for it in d["items"]]}
    if name == "get_customers":
        return customer_overview(db, org_id)
    if name == "get_funnel":
        return funnel_analysis(db, org_id)
    if name == "get_ads":
        return campaign_metrics(db, org_id)
    if name == "get_pricing":
        return pricing_recommendations(db, org_id)
    if name == "get_action_queue":
        return build_queue(db, org_id)
    if name == "simulate_price":
        return simulate_one(db, org_id, args.get("sku", ""), float(args.get("pct", 0)))
    if name == "execute_action":
        target = args.get("target")
        if str(target).isdigit():
            target = int(target)
        return exec_action(db, org_id, {"type": args.get("type"),
                                        "target": target, "params": args.get("params", {})})
    return {"error": f"bilinmeyen araç: {name}"}


# ---------------- LLM tool-calling döngüsü (OpenAI-uyumlu) ----------------
def _openai_tools():
    return [{"type": "function", "function": {
        "name": t["name"], "description": t["description"], "parameters": t["input_schema"]}}
        for t in TOOLS]


def _chat_llm(db, org_id, messages):
    convo = [{"role": "system", "content": SYSTEM}] + \
            [{"role": m["role"], "content": m["content"]} for m in messages]
    tools = _openai_tools()
    tool_log = []
    for _ in range(6):
        msg = llm.chat(convo, tools=tools, max_tokens=1500)
        calls = msg.get("tool_calls")
        if calls:
            convo.append({"role": "assistant", "content": msg.get("content"), "tool_calls": calls})
            for tc in calls:
                name = tc["function"]["name"]
                try:
                    args = json.loads(tc["function"].get("arguments") or "{}")
                except json.JSONDecodeError:
                    args = {}
                out = run_tool(db, org_id, name, args)
                tool_log.append({"tool": name, "input": args})
                convo.append({"role": "tool", "tool_call_id": tc["id"],
                              "content": json.dumps(out, ensure_ascii=False, default=str)[:6000]})
            continue
        return {"reply": (msg.get("content") or "").strip(), "tool_calls": tool_log, "mode": "llm"}
    return {"reply": "İşlem çok uzun sürdü, lütfen soruyu sadeleştir.", "tool_calls": tool_log, "mode": "llm"}


# ---------------- Anahtarsız fallback (niyet yönlendirici) ----------------
def _fallback(db, org_id, messages):
    q = (messages[-1]["content"] if messages else "")
    if isinstance(q, list):
        q = " ".join(str(x) for x in q)
    t = q.lower()
    log = []

    def used(tool):
        log.append({"tool": tool, "input": {}})

    sku_m = re.search(r"sku[-\s]?(\d{3,4})", t)
    sku = f"SKU-{sku_m.group(1)}" if sku_m else None
    pct_m = re.search(r"%\s*(-?\d+)|(-?\d+)\s*%", t)
    pct = int(next(g for g in (pct_m.groups() if pct_m else []) if g)) if pct_m else None

    # SİMÜLASYON niyeti (yazmadan ÖNCE: "ne olur / olursa / simüle" = uygulama değil)
    if sku and pct is not None and any(w in t for w in ["simül", "simul", "olursa", "ne olur", "olur mu", "etkisi"]):
        s = simulate_one(db, org_id, sku, pct)
        used("simulate_price")
        sm = s.get("simulated", {})
        return {"reply": f"{sku} %{pct}: satış %{sm.get('units_change_pct')} değişir, kâr {sm.get('profit_delta'):+,.0f}₺ (E={s.get('elasticity')}). (Bu sadece simülasyon — uygulamadım.)",
                "tool_calls": log, "mode": "fallback"}

    # YAZMA niyetleri
    if any(w in t for w in ["kapat", "durdur"]) and "kampan" in t:
        ads = campaign_metrics(db, org_id)
        cut = [c for c in ads["items"] if c["roas"] < 1]
        if cut:
            res = exec_action(db, org_id, {"type": "cut_campaign", "target": cut[0]["id"], "params": {}})
            used("execute_action")
            return {"reply": f"Zarardaki kampanyayı kapattım. {res['change']}", "tool_calls": log, "mode": "fallback"}
    if sku and pct is not None and any(w in t for w in ["fiyat", "zam", "indirim"]):
        res = exec_action(db, org_id, {"type": "adjust_price", "target": sku, "params": {"pct": pct}})
        used("execute_action")
        return {"reply": f"{sku} fiyatını güncelledim. {res['change']}", "tool_calls": log, "mode": "fallback"}
    if sku and any(w in t for w in ["stok", "sipariş", "reorder"]):
        res = exec_action(db, org_id, {"type": "reorder_stock", "target": sku, "params": {"qty": 200}})
        used("execute_action")
        return {"reply": f"{sku} için stok siparişi açtım. {res['change']}", "tool_calls": log, "mode": "fallback"}

    # OKUMA niyetleri
    if any(w in t for w in ["zarar", "kârlı", "karlı", "ürün", "sku"]):
        d = decision_scores(db, org_id); used("get_sku_profitability")
        loss = [i for i in d["items"] if i["profit"] < 0][:3]
        top = d["items"][:3]
        return {"reply": "En kârlı: " + ", ".join(f"{i['sku']} ({i['profit']:,.0f}₺)" for i in top) +
                ". Zararlı: " + (", ".join(f"{i['sku']} ({i['profit']:,.0f}₺)" for i in loss) or "yok") + ".",
                "tool_calls": log, "mode": "fallback"}
    if any(w in t for w in ["reklam", "roas", "kampan"]):
        d = campaign_metrics(db, org_id); used("get_ads")
        return {"reply": f"Blended ROAS {d['summary']['blended_roas']}x. Kapatılacak: " +
                (", ".join(c["name"] for c in d["items"] if c["roas"] < 1) or "yok") + ".",
                "tool_calls": log, "mode": "fallback"}
    if any(w in t for w in ["müşteri", "terk", "ltv", "sadık"]):
        d = customer_overview(db, org_id); used("get_customers"); s = d["summary"]
        return {"reply": f"{s['total_customers']} müşteri, ort. LTV {s['avg_ltv']:,.0f}₺, terk %{s['churn_pct']}. {s['recommendation']}",
                "tool_calls": log, "mode": "fallback"}
    if any(w in t for w in ["huni", "dönüşüm", "donusum", "checkout", "sepet"]):
        d = funnel_analysis(db, org_id); used("get_funnel")
        return {"reply": f"Darboğaz: {d['summary']['bottleneck_stage']}. {d['summary']['recommendation']}",
                "tool_calls": log, "mode": "fallback"}
    if any(w in t for w in ["fiyat", "elastik", "zam"]):
        d = pricing_recommendations(db, org_id); used("get_pricing")
        return {"reply": f"Toplam fiyat fırsatı {d['summary']['total_uplift']:,.0f}₺. " +
                (d["items"][0]["verdict"] if d["items"] else ""), "tool_calls": log, "mode": "fallback"}
    if any(w in t for w in ["aksiyon", "ne yapmal", "öneri", "yapılacak", "öncelik"]):
        d = build_queue(db, org_id); used("get_action_queue")
        return {"reply": f"Toplam {d['summary']['total_opportunity']:,.0f}₺ fırsat. İlk 3: " +
                "; ".join(f"{a['title']} (+{a['impact_monthly']:,.0f}₺)" for a in d["actions"][:3]),
                "tool_calls": log, "mode": "fallback"}
    if any(w in t for w in ["kpi", "ciro", "özet", "ozet", "satış", "durum"]):
        k = kpi_summary(db, org_id); used("get_kpi")
        return {"reply": f"Ciro {k['revenue']:,.0f}₺ (Δ%{k['revenue_delta_pct']}), {k['orders']} sipariş, "
                f"AOV {k['aov']:,.0f}₺, dönüşüm %{k['conversion_rate']}, ROAS {k['roas']}x.",
                "tool_calls": log, "mode": "fallback"}

    return {"reply": "Şunları sorabilirsin: KPI/ciro özeti, zararlı ürünler, müşteri/terk, huni, reklam/ROAS, "
            "fiyat önerileri, aksiyon kuyruğu. Aksiyon: 'SKU-1004 fiyatını %10 artır', 'zararlı kampanyayı kapat', "
            "'SKU-1011 stok sipariş et'. (Tam AI muhakemesi için LLM_API_KEY ekle.)",
            "tool_calls": log, "mode": "fallback"}


def chat(db: Session, org_id: int, messages: list) -> dict:
    if llm.available():
        try:
            return _chat_llm(db, org_id, messages)
        except Exception:
            return _fallback(db, org_id, messages)
    return _fallback(db, org_id, messages)

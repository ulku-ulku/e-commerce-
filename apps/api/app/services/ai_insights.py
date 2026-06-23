"""AI içgörü üretimi.

Akış (light RAG):
  1) KPI motoru + tahmin + karar motoru deterministik 'context' üretir
  2) Bu yapısal context LLM'e verilir -> doğal dilde içgörü + aksiyon
  3) API anahtarı yoksa deterministik fallback döner (sistem yine çalışır)
"""
import json

from app.services import llm

SYSTEM_PROMPT = (
    "Sen kıdemli bir e-ticaret büyüme analistisin. Sana verilen KPI verisi, "
    "satış tahmini ve kural-motoru sinyallerini kullanarak Türkçe, net ve "
    "aksiyona dönük içgörüler üret. Asla veri uydurma; yalnızca verilen sayıları yorumla. "
    "Yanıtı SADECE şu JSON şemasıyla ver: "
    '{"title": str, "body": str, "severity": "info|warning|critical", '
    '"actions": [{"title": str, "impact": "high|medium|low", "why": str}]}'
)


def _build_context(kpi: dict, forecast: list[dict], signals: list[dict]) -> str:
    fc = forecast[:7]
    return json.dumps({
        "kpi_son_30_gun": kpi,
        "tahmin_7_gun": [{"day": str(p["day"]), "rev": p["predicted_revenue"]} for p in fc],
        "kural_sinyalleri": signals,
    }, ensure_ascii=False, default=str)


def _fallback(kpi: dict, signals: list[dict]) -> dict:
    crit = [s for s in signals if s["severity"] == "critical"]
    sev = "critical" if crit else ("warning" if signals else "info")
    title = crit[0]["message"] if crit else f"Son 30 gün ciro: {kpi['revenue']:.0f}₺ (Δ%{kpi['revenue_delta_pct']})"
    body = " ".join(s["message"] for s in signals) or "Metrikler stabil görünüyor."
    actions = [{"title": s["action"], "impact": "high" if s["severity"] == "critical" else "medium",
                "why": s["message"]} for s in signals]
    return {"title": title, "body": body, "severity": sev, "actions": actions}


def generate_insight(kpi: dict, forecast: list[dict], signals: list[dict]) -> dict:
    if not llm.available():
        return _fallback(kpi, signals)

    try:
        msg = llm.chat(
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": "Aşağıdaki veriye göre haftalık içgörü üret:\n"
                                            + _build_context(kpi, forecast, signals)},
            ],
            max_tokens=1024,
        )
        text = (msg.get("content") or "").strip()
        # Modeli JSON'a zorladık ama güvenli ayrıştırma yapalım
        start, end = text.find("{"), text.rfind("}")
        data = json.loads(text[start:end + 1])
        data.setdefault("actions", [])
        data.setdefault("severity", "info")
        return data
    except Exception:
        # LLM hatası sistemi düşürmemeli
        return _fallback(kpi, signals)

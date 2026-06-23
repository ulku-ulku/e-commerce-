"""Aksiyon Kuyruğu — tüm domain'lerden gelen sinyalleri TEK, ₺-etkisine göre sıralı listede toplar.

Her aksiyon: tahmini aylık ₺ etki + çaba + GÜVEN (#5) + çalıştırılabilir komut (#4 agency).
Yüksek etkili/kritik/düşük güvenli aksiyonlar onay (confirm) gerektirir.
"""
import math

from sqlalchemy.orm import Session

from app.services.ad_engine import campaign_metrics
from app.services.confidence import confidence
from app.services.customer_analytics import customer_overview
from app.services.decision_score import decision_scores
from app.services.elasticity import pricing_recommendations
from app.services.funnel import funnel_analysis
from app.services.profitability import sku_profitability

EFFORT_W = {"low": 1.0, "med": 1.6, "high": 2.4}
HIGH_IMPACT = 50_000  # bu eşiğin üstü onay gerektirir


def build_queue(db: Session, org_id: int, days: int = 30) -> dict:
    actions = []

    def add(domain, title, detail, impact, effort, severity, sample, full_at, exec_spec):
        conf = confidence(sample, full_at)
        impact = abs(impact)
        requires_confirm = severity == "critical" or impact >= HIGH_IMPACT or conf["level"] == "low"
        actions.append({
            "domain": domain, "title": title, "detail": detail,
            "impact_monthly": round(impact, 2), "effort": effort, "severity": severity,
            "priority": round(impact / EFFORT_W[effort], 2),
            "confidence": conf, "exec": exec_spec, "requires_confirm": requires_confirm,
        })

    pr = pricing_recommendations(db, org_id, days)
    pmap = {p["sku"]: p["recommended_pct"] for p in pr["items"]}

    # --- Kârlılık: zararlı SKU'lar ---
    ds = decision_scores(db, org_id, days)
    for s in ds["items"]:
        if s["profit"] < 0:
            pct = pmap.get(s["sku"]) or 15
            add("Kârlılık", f"{s['sku']} zararını durdur",
                f"{s['units']} adet satıyor ama {s['profit']:,.0f}₺ zarar (marj %{s['margin']}).",
                -s["profit"], "med", "critical", s["units"], 50,
                {"type": "adjust_price", "target": s["sku"], "params": {"pct": pct}, "auto": True})
        elif s["components"]["stok_riski"] > 0.5:
            ppu = s["profit"] / s["units"] if s["units"] else 0
            gap_days = max(0, s["lead_time_days"] - s["days_of_stock"])
            daily = s["units"] / days
            reorder = math.ceil(daily * s["lead_time_days"] * 1.5)
            add("Operasyon", f"{s['sku']} için stok siparişi aç",
                f"~{s['days_of_stock']:.0f} gün stok kaldı (tedarik {s['lead_time_days']}g).",
                gap_days * daily * ppu, "low", "warning", s["units"], 50,
                {"type": "reorder_stock", "target": s["sku"], "params": {"qty": reorder}, "auto": True})

    # --- Reklam: zararda kampanyalar ---
    ads = campaign_metrics(db, org_id)
    for c in ads["items"]:
        if c["roas"] < 1:
            add("Reklam", f"'{c['name']}' kampanyasını kapat",
                f"ROAS {c['roas']}x — {c['spend']:,.0f}₺ harcama, {c['revenue']:,.0f}₺ getiri.",
                c["spend"] - c["revenue"], "low", "critical", c["conversions"], 20,
                {"type": "cut_campaign", "target": c["id"], "params": {}, "auto": True})

    # --- Fiyat: elastikiyet fırsatları ---
    for it in pr["items"][:3]:
        if it["recommended_pct"] != 0 and it["profit_uplift"] > 0:
            add("Fiyat", f"{it['sku']} fiyatını %{it['recommended_pct']} ayarla",
                it["verdict"], it["profit_uplift"], "low", "info", it["units"], 50,
                {"type": "adjust_price", "target": it["sku"],
                 "params": {"pct": it["recommended_pct"]}, "auto": True})

    # --- Trafik: checkout darboğazı (manuel) ---
    fn = funnel_analysis(db, org_id, days)
    st = {s["key"]: s for s in fn["stages"]}
    if fn["summary"]["bottleneck_stage"] and "purchases" in st:
        skus = sku_profitability(db, org_id, days)
        net = sum(s["net_sales"] for s in skus)
        margin = (sum(s["profit"] for s in skus) / net) if net else 0.15
        aov = net / sum(s["units"] for s in skus) if skus else 0
        checkout = st.get("checkout_started", {}).get("count", 0)
        cur_rate = st["purchases"]["count"] / checkout if checkout else 0
        impact = checkout * max(0, 0.45 - cur_rate) * aov * margin
        if impact > 0:
            add("Trafik", "Ödeme (checkout) sayfasını iyileştir",
                fn["summary"]["recommendation"], impact, "high", "warning", checkout, 300,
                {"type": "manual", "target": "checkout", "params": {}, "auto": False})

    # --- Müşteri: terk riski (manuel kampanya) ---
    cu = customer_overview(db, org_id)
    if cu["summary"]:
        churn = cu["summary"]["churn_pct"]
        ltv = cu["summary"]["avg_ltv"]
        at_risk_n = next((s["count"] for s in cu["segments"] if s["segment"] == "at_risk"), 0)
        if churn > 10 and at_risk_n:
            add("Müşteri", "Terk riskli müşterileri elde tut",
                f"{at_risk_n} müşteri terk riskinde — sadakat/e-posta kampanyası.",
                at_risk_n * ltv * 0.15, "med", "warning", at_risk_n, 30,
                {"type": "manual", "target": "retention", "params": {}, "auto": False})

    actions.sort(key=lambda a: a["impact_monthly"], reverse=True)
    for i, a in enumerate(actions):
        a["id"] = i + 1
    total = sum(a["impact_monthly"] for a in actions)
    return {"summary": {"total_opportunity": round(total, 2), "action_count": len(actions),
                        "low_confidence": sum(1 for a in actions if a["confidence"]["level"] == "low")},
            "actions": actions}

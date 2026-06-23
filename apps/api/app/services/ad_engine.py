"""Reklam motoru (domain 5) — kampanya başına ROAS, CAC, payback + karar.

Karar: ROAS<1 zararda -> KAPAT; CAC>LTV sürdürülemez; ROAS>=4 ölçekle.
"""
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models import AdCampaign, Customer

ASSUMED_MARGIN = 0.25  # katkı marjı varsayımı (payback için); prod'da SKU marjından gelir


def campaign_metrics(db: Session, org_id: int) -> dict:
    avg_ltv = db.query(func.coalesce(func.avg(Customer.ltv), 0.0)).filter(
        Customer.org_id == org_id).scalar() or 0.0

    rows = db.query(AdCampaign).filter(AdCampaign.org_id == org_id).all()
    items = []
    for c in rows:
        roas = (c.revenue / c.spend) if c.spend else 0.0
        cac = (c.spend / c.new_customers) if c.new_customers else None
        ctr = (c.clicks / c.impressions * 100) if c.impressions else 0.0
        cvr = (c.conversions / c.clicks * 100) if c.clicks else 0.0
        aov = (c.revenue / c.conversions) if c.conversions else 0.0
        # payback: CAC'yi kaç siparişlik katkı marjı geri öder
        per_order_margin = aov * ASSUMED_MARGIN
        payback_orders = (cac / per_order_margin) if (cac and per_order_margin) else None

        if roas < 1:
            rec, sev = ("🔴 ZARARDA — kampanyayı KAPAT", "critical")
        elif cac and avg_ltv and cac > avg_ltv:
            rec, sev = (f"CAC ({cac:.0f}₺) > LTV ({avg_ltv:.0f}₺) — sürdürülemez, durdur", "critical")
        elif roas < 2:
            rec, sev = ("🟡 Düşük verim — bütçeyi kıs, hedeflemeyi daralt", "warning")
        elif roas >= 4:
            rec, sev = ("✅ Ölçekle — bütçeyi artır", "info")
        else:
            rec, sev = ("→ İzle", "info")

        items.append({
            "id": c.id, "name": c.name, "platform": c.platform, "status": c.status,
            "spend": round(c.spend, 2), "revenue": round(c.revenue, 2),
            "roas": round(roas, 2), "cac": round(cac, 2) if cac else None,
            "ctr": round(ctr, 2), "cvr": round(cvr, 2),
            "conversions": c.conversions, "new_customers": c.new_customers,
            "payback_orders": round(payback_orders, 1) if payback_orders else None,
            "recommendation": rec, "severity": sev,
        })

    items.sort(key=lambda x: x["roas"])  # en kötü ROAS üstte (önce müdahale)
    total_spend = sum(i["spend"] for i in items)
    total_rev = sum(i["revenue"] for i in items)
    summary = {
        "total_spend": round(total_spend, 2),
        "total_revenue": round(total_rev, 2),
        "blended_roas": round(total_rev / total_spend, 2) if total_spend else 0.0,
        "campaigns_to_cut": sum(1 for i in items if i["severity"] == "critical"),
        "avg_ltv": round(avg_ltv, 2),
    }
    return {"summary": summary, "items": items}

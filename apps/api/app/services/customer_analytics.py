"""Müşteri analitiği (domain 3) — LTV, tekrar oranı, terk riski.

Karar: CAC > LTV veya terk yüksekse "yeni müşteri alma yerine mevcut müşteriyi tut".
"""
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models import Customer


def customer_overview(db: Session, org_id: int) -> dict:
    q = db.query(Customer).filter(Customer.org_id == org_id)
    total = q.count()
    if not total:
        return {"summary": {}, "segments": [], "top_customers": [], "at_risk": []}

    avg_ltv = db.query(func.coalesce(func.avg(Customer.ltv), 0.0)).filter(
        Customer.org_id == org_id).scalar() or 0.0
    repeat = q.filter(Customer.orders_count >= 2).count()
    at_risk_n = q.filter(Customer.segment == "at_risk").count()

    seg_rows = db.query(Customer.segment, func.count(Customer.id),
                        func.coalesce(func.sum(Customer.ltv), 0.0)).filter(
        Customer.org_id == org_id).group_by(Customer.segment).all()
    segments = [{"segment": s, "count": n, "ltv": round(float(v), 2)} for s, n, v in seg_rows]

    top = q.order_by(Customer.ltv.desc()).limit(8).all()
    top_customers = [{"external_id": c.external_id, "city": c.city, "segment": c.segment,
                      "orders": c.orders_count, "ltv": round(c.ltv, 2)} for c in top]

    risk = q.filter(Customer.segment == "at_risk").order_by(Customer.ltv.desc()).limit(8).all()
    at_risk = [{"external_id": c.external_id, "city": c.city, "ltv": round(c.ltv, 2),
                "last_order": str(c.last_order_date)} for c in risk]

    churn_pct = at_risk_n / total * 100
    if churn_pct > 15:
        rec = "Terk oranı yüksek — yeni müşteri almak yerine mevcut müşteriyi elde tut (e-posta/sadakat)."
    else:
        rec = "Terk kontrol altında — VIP segmenti büyütmeye odaklan."

    summary = {
        "total_customers": total,
        "avg_ltv": round(avg_ltv, 2),
        "repeat_rate": round(repeat / total * 100, 1),
        "churn_pct": round(churn_pct, 1),
        "recommendation": rec,
    }
    return {"summary": summary, "segments": segments,
            "top_customers": top_customers, "at_risk": at_risk}

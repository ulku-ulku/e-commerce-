"""Trafik & dönüşüm hunisi (domain 4) — darboğaz tespiti.

En düşük aşama-geçiş oranı = darboğaz. Karar örneği: "ürün değil, ödeme sayfası problem".
"""
from datetime import date, timedelta

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models import FunnelDaily

STAGES = [
    ("visitors", "Ziyaretçi"),
    ("product_views", "Ürün Görüntüleme"),
    ("add_to_cart", "Sepete Ekleme"),
    ("checkout_started", "Ödemeye Başlama"),
    ("purchases", "Satın Alma"),
]

# Hangi geçiş darboğazsa hangi karar
BOTTLENECK_REC = {
    "product_views": "Trafik alakasız / landing zayıf — kaynak & hedeflemeyi gözden geçir.",
    "add_to_cart": "Ürün sayfası ikna etmiyor — görsel, fiyat, sosyal kanıt iyileştir.",
    "checkout_started": "Sepette kayıp — kargo/ek maliyet sürprizi; ücretsiz kargo eşiği dene.",
    "purchases": "⚠ Ödeme sayfası problem — ürün değil checkout! Ödeme yöntemleri & hız düzelt.",
}


def funnel_analysis(db: Session, org_id: int, days: int = 30) -> dict:
    start = date.today() - timedelta(days=days - 1)
    cols = [func.coalesce(func.sum(getattr(FunnelDaily, k)), 0) for k, _ in STAGES]
    row = db.query(*cols).filter(
        FunnelDaily.org_id == org_id, FunnelDaily.day >= start).one()
    totals = [int(x) for x in row]

    stages, worst_rate, worst_key = [], 2.0, None
    for i, (key, label) in enumerate(STAGES):
        count = totals[i]
        if i == 0:
            rate = 100.0
        else:
            prev = totals[i - 1]
            rate = (count / prev * 100) if prev else 0.0
            if rate < worst_rate * 100:
                worst_rate, worst_key = rate / 100, key
        stages.append({"key": key, "label": label, "count": count,
                       "step_rate": round(rate, 1)})

    overall = (totals[-1] / totals[0] * 100) if totals[0] else 0.0
    summary = {
        "overall_conversion": round(overall, 2),
        "bottleneck_stage": next((s["label"] for s in stages if s["key"] == worst_key), None),
        "bottleneck_rate": round(worst_rate * 100, 1) if worst_key else None,
        "recommendation": BOTTLENECK_REC.get(worst_key, "Huni dengeli görünüyor."),
    }
    return {"summary": summary, "stages": stages}

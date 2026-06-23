"""Karar Skoru motoru.

Kullanıcının formülü:
  Decision Score = (Kâr Potansiyeli × Güven) − Stok Riski − Müşteri Kaybı − Reklam İsrafı

Her bileşen 0..1'e normalize edilir, ağırlıklandırılıp 0..100 skora indirgenir.
Çıktı: SKU başına skor + somut aksiyon önerisi ("çok satıyor ama zarar yazıyor" vb.).
"""
from datetime import date, timedelta

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models import Customer, OrderItem
from app.services.profitability import sku_profitability


def _clamp(x, lo=0.0, hi=1.0):
    return max(lo, min(hi, x))


def _customer_loss_ratio(db: Session, org_id: int) -> float:
    total = db.query(func.count(Customer.id)).filter(Customer.org_id == org_id).scalar() or 0
    if not total:
        return 0.0
    at_risk = db.query(func.count(Customer.id)).filter(
        Customer.org_id == org_id, Customer.segment == "at_risk").scalar() or 0
    return at_risk / total


def _sku_repeat_ratio(db: Session, org_id: int, days: int) -> dict:
    """SKU'yu satın alan müşterilerin tekrar oranı (düşükse müşteri kaybı sinyali)."""
    start = date.today() - timedelta(days=days - 1)
    rows = db.query(
        OrderItem.sku,
        func.count(func.distinct(OrderItem.customer_id)),
        func.count(OrderItem.id),
    ).filter(OrderItem.org_id == org_id, OrderItem.day >= start).group_by(OrderItem.sku).all()
    out = {}
    for sku, buyers, lines in rows:
        out[sku] = (lines / buyers) if buyers else 1.0  # >1 = tekrar var
    return out


def decision_scores(db: Session, org_id: int, days: int = 30) -> dict:
    skus = sku_profitability(db, org_id, days)
    if not skus:
        return {"summary": {}, "items": []}

    org_churn = _customer_loss_ratio(db, org_id)
    repeat = _sku_repeat_ratio(db, org_id, days)
    max_units = max((s["units"] for s in skus), default=1) or 1
    units_sorted = sorted(s["units"] for s in skus)
    median_units = units_sorted[len(units_sorted) // 2] or 1

    items = []
    for s in skus:
        # --- Bileşenler (0..1, PP negatif olabilir) ---
        pp = _clamp(s["margin"] / 30.0, -1.0, 1.0)                 # Kâr Potansiyeli
        confidence = _clamp(s["units"] / (median_units * 2))       # Güven (veri hacmi)
        stock_risk = _clamp((s["lead_time_days"] - s["days_of_stock"]) / s["lead_time_days"]) \
            if s["days_of_stock"] < 900 else 0.0                   # Stok Riski
        sku_repeat = repeat.get(s["sku"], 1.0)
        cust_loss = _clamp(org_churn + (0.3 if sku_repeat < 1.2 else 0.0))  # Müşteri Kaybı
        ad_ratio = (s["ad_cost"] / s["net_sales"]) if s["net_sales"] else 0.0
        ad_waste = _clamp(ad_ratio) * (1.0 if s["margin"] < 10 else 0.3)    # Reklam İsrafı

        # --- Skor: (PP × Güven) − cezalar, 0..100 ---
        raw = pp * confidence * 100 - stock_risk * 40 - cust_loss * 20 - ad_waste * 30
        score = int(_clamp(raw, 0, 100))

        # --- Aksiyon önerisi ---
        popular = s["units"] >= median_units
        if s["margin"] < 0 and popular:
            rec, sev = ("⚠ Çok satıyor ama ZARAR yazıyor — fiyatı artır / maliyeti düşür / reklamı kes", "critical")
        elif s["margin"] < 0:
            rec, sev = ("Zararda — fiyat/maliyet revize et veya listeden çıkar", "warning")
        elif stock_risk > 0.5:
            rec, sev = (f"📦 Stok riski: ~{s['days_of_stock']:.0f} gün kaldı (tedarik {s['lead_time_days']}g) — sipariş aç", "warning")
        elif ad_waste > 0.4:
            rec, sev = ("💸 Reklam israfı — bu SKU'da bütçeyi kıs", "warning")
        elif score >= 70:
            rec, sev = ("✅ Yıldız ürün — stok + reklam bütçesini ölçekle", "info")
        else:
            rec, sev = ("→ İzle", "info")

        items.append({
            **s, "decision_score": score, "recommendation": rec, "severity": sev,
            "components": {
                "kar_potansiyeli": round(pp, 2), "guven": round(confidence, 2),
                "stok_riski": round(stock_risk, 2), "musteri_kaybi": round(cust_loss, 2),
                "reklam_israfi": round(ad_waste, 2),
            },
        })

    items.sort(key=lambda x: x["decision_score"], reverse=True)

    total_profit = sum(s["profit"] for s in skus)
    total_net = sum(s["net_sales"] for s in skus)
    summary = {
        "total_profit": round(total_profit, 2),
        "avg_margin": round(total_profit / total_net * 100, 2) if total_net else 0.0,
        "loss_making_skus": sum(1 for s in skus if s["profit"] < 0),
        "stock_risk_skus": sum(1 for i in items if i["components"]["stok_riski"] > 0.5),
        "total_skus": len(skus),
        "customer_churn_pct": round(org_churn * 100, 1),
    }
    return {"summary": summary, "items": items}

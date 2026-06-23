"""Aksiyon yürütücü (#4 agency).

Önerileri sadece kaydetmek yerine GERÇEKTEN uygular (sandbox'ta DB'yi değiştirir) ve
before→after farkını döndürür. Gerçek entegrasyonda burası Meta/Trendyol write-API'lerine bağlanır.
Riskli aksiyonlar API katmanında confirm gerektirir (guardrail).
"""
from sqlalchemy.orm import Session

from app.models import AdCampaign, Product


def execute(db: Session, org_id: int, spec: dict) -> dict:
    t = spec.get("type")
    target = spec.get("target")
    params = spec.get("params", {})

    if t == "cut_campaign":
        c = db.query(AdCampaign).filter(
            AdCampaign.org_id == org_id, AdCampaign.id == target).first()
        if not c:
            return {"ok": False, "change": "Kampanya bulunamadı"}
        before = c.status
        c.status = "paused"
        db.commit()
        return {"ok": True, "change": f"'{c.name}' durumu: {before} → paused"}

    if t == "reorder_stock":
        p = db.query(Product).filter(
            Product.org_id == org_id, Product.sku == target).first()
        if not p:
            return {"ok": False, "change": "SKU bulunamadı"}
        qty = int(params.get("qty", 0))
        before = p.stock
        p.stock = before + qty
        db.commit()
        return {"ok": True, "change": f"{target} stok: {before} → {p.stock} (+{qty})"}

    if t == "adjust_price":
        p = db.query(Product).filter(
            Product.org_id == org_id, Product.sku == target).first()
        if not p:
            return {"ok": False, "change": "SKU bulunamadı"}
        pct = float(params.get("pct", 0))
        before = p.price
        p.price = round(before * (1 + pct / 100), 2)
        db.commit()
        return {"ok": True, "change": f"{target} fiyat: {before:.0f}₺ → {p.price:.0f}₺ (%{pct:+.0f})"}

    if t == "manual":
        # Otomatik uygulanamaz (ör. checkout düzeltme, retention kampanyası) — plan olarak işaretlenir
        return {"ok": True, "change": "Manuel aksiyon — plana eklendi (otomatik uygulanmaz)", "manual": True}

    return {"ok": False, "change": f"Bilinmeyen aksiyon tipi: {t}"}

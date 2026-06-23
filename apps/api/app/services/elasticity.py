"""Fiyat elastikiyeti & what-if simülasyonu (domain 7 — "betimleyici"den "prescriptive"e).

Elastikiyet (E) tahmini: kategori taban katsayısı × rakip-fiyat konumu düzeltmesi.
Simülasyon: %Δ fiyat -> talep değişimi (E×Δ) -> yeni ciro/kâr.
Optimal: kârı maksimize eden fiyat hamlesini tarar.
"""
from sqlalchemy.orm import Session

from app.models import Product
from app.services.profitability import sku_profitability

# Kategori taban elastikiyeti (negatif: fiyat artınca talep düşer; daha negatif = daha hassas)
CATEGORY_E = {
    "Elektronik": -1.3, "Giyim": -1.6, "Kozmetik": -0.9,
    "Ev & Yaşam": -1.1, "Spor": -1.2, "Aksesuar": -1.4,
}


def estimate_elasticity(category: str, price: float, competitor: float | None) -> float:
    e = CATEGORY_E.get(category, -1.2)
    if competitor and competitor > 0:
        if price > competitor * 1.05:      # rakibinden pahalı -> daha hassas
            e *= 1.3
        elif price < competitor * 0.95:    # rakibinden ucuz -> daha az hassas
            e *= 0.8
    return round(e, 2)


def _simulate(units: int, price: float, profit: float, e: float, pct: float) -> dict:
    """pct: fiyat değişimi yüzdesi (+ zam / − indirim)."""
    profit_per_unit = (profit / units) if units else 0.0
    unit_all_in_cost = price - profit_per_unit          # komisyon/reklam/kargo dahil efektif maliyet
    demand_factor = max(0.0, 1 + e * (pct / 100))       # E negatif
    new_units = units * demand_factor
    new_price = price * (1 + pct / 100)
    new_profit = new_units * (new_price - unit_all_in_cost)
    return {
        "pct": pct,
        "units": round(new_units),
        "units_change_pct": round((demand_factor - 1) * 100, 1),
        "revenue": round(new_units * new_price, 2),
        "profit": round(new_profit, 2),
        "profit_delta": round(new_profit - profit, 2),
    }


def _optimal(units: int, price: float, profit: float, e: float) -> dict:
    best = {"pct": 0, "profit_delta": 0.0}
    for step in range(-15, 26):                          # -%15 ... +%25
        sim = _simulate(units, price, profit, e, step)
        if sim["profit_delta"] > best["profit_delta"]:
            best = sim
    return best


def pricing_recommendations(db: Session, org_id: int, days: int = 30) -> dict:
    skus = sku_profitability(db, org_id, days)
    products = {p.sku: p for p in db.query(Product).filter(Product.org_id == org_id).all()}
    items = []
    for s in skus:
        p = products.get(s["sku"])
        if not p or s["units"] == 0:
            continue
        e = estimate_elasticity(s["category"], p.price, p.competitor_price)
        opt = _optimal(s["units"], p.price, s["profit"], e)
        verdict = "Fiyat optimum" if opt["pct"] == 0 else (
            f"%{opt['pct']} {'zam' if opt['pct'] > 0 else 'indirim'} öner: "
            f"satış %{abs(opt['units_change_pct'])} {'düşer' if opt['units_change_pct'] < 0 else 'artar'} "
            f"ama kâr {opt['profit_delta']:+,.0f}₺")
        items.append({
            "sku": s["sku"], "category": s["category"], "price": p.price,
            "competitor_price": p.competitor_price, "elasticity": e,
            "units": s["units"], "current_profit": s["profit"],
            "recommended_pct": opt["pct"], "profit_uplift": opt["profit_delta"],
            "verdict": verdict,
        })
    items.sort(key=lambda x: x["profit_uplift"], reverse=True)
    total_uplift = sum(i["profit_uplift"] for i in items)
    return {"summary": {"total_uplift": round(total_uplift, 2),
                        "actionable": sum(1 for i in items if i["recommended_pct"] != 0)},
            "items": items}


def simulate_one(db: Session, org_id: int, sku: str, pct: float, days: int = 30) -> dict:
    skus = {s["sku"]: s for s in sku_profitability(db, org_id, days)}
    p = db.query(Product).filter(Product.org_id == org_id, Product.sku == sku).first()
    s = skus.get(sku)
    if not p or not s:
        return {"error": "SKU bulunamadı"}
    e = estimate_elasticity(s["category"], p.price, p.competitor_price)
    cur = {"pct": 0, "units": s["units"], "revenue": round(s["units"] * p.price, 2),
           "profit": s["profit"]}
    return {"sku": sku, "elasticity": e, "current": cur,
            "simulated": _simulate(s["units"], p.price, s["profit"], e, pct)}

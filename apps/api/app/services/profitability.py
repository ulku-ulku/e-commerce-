"""Kârlılık motoru (domain 2 + 6).

SKU bazında gerçek net kârı hesaplar:
  net_sales - (ürün maliyeti + paketleme + kargo + komisyon + reklam + iade) = kâr
Ayrıca stok/hız ile stok riskini çıkarır.
"""
from datetime import date, timedelta

from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from app.models import OrderItem, Product


def sku_profitability(db: Session, org_id: int, days: int = 30) -> list[dict]:
    end = date.today()
    start = end - timedelta(days=days - 1)

    rows = db.execute(
        select(
            OrderItem.sku,
            OrderItem.category,
            func.sum(OrderItem.qty),
            func.sum(OrderItem.net_sales),
            func.sum(OrderItem.unit_price * OrderItem.qty),
            func.sum(OrderItem.discount),
            func.sum(OrderItem.shipping_cost),
            func.sum(OrderItem.commission),
            func.sum(OrderItem.ad_cost),
            func.sum(case((OrderItem.returned == True, OrderItem.qty), else_=0)),  # noqa: E712
        ).where(
            OrderItem.org_id == org_id,
            OrderItem.day >= start, OrderItem.day <= end,
        ).group_by(OrderItem.sku, OrderItem.category)
    ).all()

    products = {p.sku: p for p in db.query(Product).filter(Product.org_id == org_id).all()}
    out = []
    for r in rows:
        sku, category, units, net, gross, disc, ship, comm, ad, returns = r
        units = int(units or 0)
        net = float(net or 0)
        p = products.get(sku)
        unit_cost = p.unit_cost if p else 0.0
        pack = p.packaging_cost if p else 0.0
        stock = p.stock if p else 0
        lead = p.lead_time_days if p else 14

        cogs = unit_cost * units
        packaging = pack * units
        return_cost = float(returns or 0) * (unit_cost + (ship / units if units else 0))
        total_cost = cogs + packaging + float(ship or 0) + float(comm or 0) + float(ad or 0) + return_cost
        profit = net - total_cost
        margin = (profit / net * 100) if net else 0.0

        daily_velocity = units / days if units else 0.0
        days_of_stock = (stock / daily_velocity) if daily_velocity else 999.0

        out.append({
            "sku": sku, "category": category, "units": units,
            "net_sales": round(net, 2),
            "cogs": round(cogs, 2), "ad_cost": round(float(ad or 0), 2),
            "commission": round(float(comm or 0), 2), "shipping": round(float(ship or 0), 2),
            "profit": round(profit, 2), "margin": round(margin, 2),
            "stock": stock, "lead_time_days": lead,
            "days_of_stock": round(days_of_stock, 1),
            "price": p.price if p else 0.0,
            "competitor_price": p.competitor_price if p else None,
        })
    return out

"""Değişim/Büyüme oranları (büyüme-küçülme, WoW/MoM).

Bu dönem vs önceki dönem karşılaştırması:
  - genel ciro/sipariş değişimi
  - kanal bazında büyüme-küçülme (sales_records)
  - kategori bazında (order_items)
  - en çok büyüyen / küçülen SKU'lar
"""
from datetime import date, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import OrderItem, SalesRecord


def _pct(cur: float, prev: float) -> float:
    if not prev:
        return 100.0 if cur > 0 else 0.0
    return round((cur - prev) / prev * 100, 1)


def growth_analysis(db: Session, org_id: int, days: int = 7) -> dict:
    today = date.today()
    cur_start = today - timedelta(days=days - 1)
    prev_end = cur_start - timedelta(days=1)
    prev_start = prev_end - timedelta(days=days - 1)
    period_label = "Hafta (7g)" if days == 7 else f"{days} gün"

    def overall(start, end):
        r = db.execute(select(
            func.coalesce(func.sum(SalesRecord.revenue), 0.0),
            func.coalesce(func.sum(SalesRecord.orders), 0),
        ).where(SalesRecord.org_id == org_id, SalesRecord.day >= start, SalesRecord.day <= end)).one()
        return float(r[0]), int(r[1])

    cr, co = overall(cur_start, today)
    pr, po = overall(prev_start, prev_end)

    def by(col, table, valcol, start, end):
        rows = db.execute(select(col, func.coalesce(func.sum(valcol), 0.0)).where(
            table.org_id == org_id, table.day >= start, table.day <= end).group_by(col)).all()
        return {k: float(v) for k, v in rows}

    # Kanal (sales_records)
    cc = by(SalesRecord.channel, SalesRecord, SalesRecord.revenue, cur_start, today)
    pc = by(SalesRecord.channel, SalesRecord, SalesRecord.revenue, prev_start, prev_end)
    channels = sorted(
        [{"name": k, "current": round(cc.get(k, 0), 2), "previous": round(pc.get(k, 0), 2),
          "change_pct": _pct(cc.get(k, 0), pc.get(k, 0))} for k in set(cc) | set(pc)],
        key=lambda x: x["current"], reverse=True)

    # Kategori (order_items)
    ccat = by(OrderItem.category, OrderItem, OrderItem.net_sales, cur_start, today)
    pcat = by(OrderItem.category, OrderItem, OrderItem.net_sales, prev_start, prev_end)
    categories = sorted(
        [{"name": k, "current": round(ccat.get(k, 0), 2), "previous": round(pcat.get(k, 0), 2),
          "change_pct": _pct(ccat.get(k, 0), pcat.get(k, 0))} for k in set(ccat) | set(pcat)],
        key=lambda x: x["change_pct"], reverse=True)

    # SKU (order_items) -> en çok büyüyen / küçülen
    csku = by(OrderItem.sku, OrderItem, OrderItem.net_sales, cur_start, today)
    psku = by(OrderItem.sku, OrderItem, OrderItem.net_sales, prev_start, prev_end)
    skus = [{"sku": k, "current": round(csku.get(k, 0), 2), "previous": round(psku.get(k, 0), 2),
             "change_pct": _pct(csku.get(k, 0), psku.get(k, 0))}
            for k in set(csku) | set(psku) if (csku.get(k, 0) + psku.get(k, 0)) > 0]
    skus.sort(key=lambda x: x["change_pct"], reverse=True)

    return {
        "summary": {
            "period_label": period_label,
            "revenue_current": round(cr, 2), "revenue_previous": round(pr, 2),
            "revenue_change_pct": _pct(cr, pr),
            "orders_change_pct": _pct(co, po),
        },
        "channels": channels,
        "categories": categories,
        "top_growing": skus[:5],
        "top_shrinking": list(reversed(skus[-5:])) if len(skus) >= 5 else skus[::-1],
    }

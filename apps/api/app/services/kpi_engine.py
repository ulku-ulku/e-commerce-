"""KPI hesaplama motoru — ham SalesRecord'lardan türetilmiş metrikler."""
from datetime import date, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import SalesRecord


def _agg(db: Session, org_id: int, start: date, end: date) -> dict:
    row = db.execute(
        select(
            func.coalesce(func.sum(SalesRecord.revenue), 0.0),
            func.coalesce(func.sum(SalesRecord.orders), 0),
            func.coalesce(func.sum(SalesRecord.sessions), 0),
            func.coalesce(func.sum(SalesRecord.ad_spend), 0.0),
        ).where(
            SalesRecord.org_id == org_id,
            SalesRecord.day >= start,
            SalesRecord.day <= end,
        )
    ).one()
    return {"revenue": float(row[0]), "orders": int(row[1]),
            "sessions": int(row[2]), "ad_spend": float(row[3])}


def kpi_summary(db: Session, org_id: int, days: int = 30) -> dict:
    end = date.today()
    start = end - timedelta(days=days - 1)
    prev_end = start - timedelta(days=1)
    prev_start = prev_end - timedelta(days=days - 1)

    cur = _agg(db, org_id, start, end)
    prev = _agg(db, org_id, prev_start, prev_end)

    aov = cur["revenue"] / cur["orders"] if cur["orders"] else 0.0
    conv = (cur["orders"] / cur["sessions"] * 100) if cur["sessions"] else 0.0
    roas = cur["revenue"] / cur["ad_spend"] if cur["ad_spend"] else 0.0
    delta = ((cur["revenue"] - prev["revenue"]) / prev["revenue"] * 100) if prev["revenue"] else 0.0

    return {
        **cur,
        "aov": round(aov, 2),
        "conversion_rate": round(conv, 2),
        "roas": round(roas, 2),
        "revenue_delta_pct": round(delta, 2),
    }


def timeseries(db: Session, org_id: int, days: int = 30) -> list[dict]:
    end = date.today()
    start = end - timedelta(days=days - 1)
    rows = db.execute(
        select(
            SalesRecord.day,
            func.sum(SalesRecord.revenue),
            func.sum(SalesRecord.orders),
        ).where(
            SalesRecord.org_id == org_id,
            SalesRecord.day >= start,
            SalesRecord.day <= end,
        ).group_by(SalesRecord.day).order_by(SalesRecord.day)
    ).all()
    return [{"day": r[0], "revenue": float(r[1]), "orders": int(r[2])} for r in rows]

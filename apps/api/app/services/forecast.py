"""Satış tahmini — MVP: lineer trend + 7 günlük mevsimsellik düzeltmesi.
İleride Prophet/XGBoost ile değiştirilebilecek tek arayüz."""
from datetime import date, timedelta

from sqlalchemy.orm import Session

from app.services.kpi_engine import timeseries


def forecast_revenue(db: Session, org_id: int, horizon: int = 14) -> list[dict]:
    series = timeseries(db, org_id, days=60)
    if len(series) < 7:
        return []

    ys = [p["revenue"] for p in series]
    n = len(ys)

    # Basit en küçük kareler lineer trend
    xs = list(range(n))
    mean_x = sum(xs) / n
    mean_y = sum(ys) / n
    denom = sum((x - mean_x) ** 2 for x in xs) or 1.0
    slope = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, ys)) / denom
    intercept = mean_y - slope * mean_x

    # Haftalık mevsimsellik faktörü (gün-of-week ortalama / genel ortalama)
    dow_sum = {i: [] for i in range(7)}
    for p in series:
        dow_sum[p["day"].weekday()].append(p["revenue"])
    dow_factor = {
        d: (sum(v) / len(v) / mean_y if v and mean_y else 1.0)
        for d, v in dow_sum.items()
    }

    out = []
    last_day = series[-1]["day"]
    for h in range(1, horizon + 1):
        d = last_day + timedelta(days=h)
        base = intercept + slope * (n - 1 + h)
        pred = max(0.0, base * dow_factor.get(d.weekday(), 1.0))
        out.append({"day": d, "predicted_revenue": round(pred, 2)})
    return out

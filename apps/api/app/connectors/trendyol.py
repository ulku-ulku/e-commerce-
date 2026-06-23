"""Trendyol connector (TR pazaryeri).

live  : Supplier API (Basic Auth: apiKey:apiSecret). config: {supplier_id, api_key, api_secret}
sandbox: gerçekçi sahte sipariş üretir (anahtar gerekmez).
"""
import math
import random
from datetime import date, datetime, timedelta, timezone

from app.connectors.base import BaseConnector


class TrendyolConnector(BaseConnector):
    kind = "trendyol"

    def fetch(self, since: date) -> list[dict]:
        if self.mode == "live":
            return self._fetch_live(since)
        return self._fetch_sandbox(since)

    def _fetch_live(self, since: date) -> list[dict]:
        import httpx
        sid = self.config["supplier_id"]
        key = self.config["api_key"]
        secret = self.config["api_secret"]
        start_ms = int(datetime(since.year, since.month, since.day,
                                tzinfo=timezone.utc).timestamp() * 1000)
        url = f"https://api.trendyol.com/sapigw/suppliers/{sid}/orders"
        params = {"startDate": start_ms, "size": 200, "orderByField": "PackageLastModifiedDate"}
        with httpx.Client(timeout=30) as c:
            r = c.get(url, params=params, auth=(key, secret),
                      headers={"User-Agent": f"{sid} - Commerce-AI"})
            r.raise_for_status()
            return r.json().get("content", [])

    def _fetch_sandbox(self, since: date) -> list[dict]:
        orders = []
        days = (date.today() - since).days + 1
        for i in range(days):
            d = since + timedelta(days=i)
            ts = int(datetime(d.year, d.month, d.day, tzinfo=timezone.utc).timestamp() * 1000)
            weekend = 1.4 if d.weekday() >= 5 else 1.0
            n = int((30 + 10 * math.sin(i / 7 * 2 * math.pi)) * weekend * random.uniform(0.9, 1.12))
            for _ in range(max(0, n)):
                gross = round((120 + (i % 20) * 5) * random.uniform(0.92, 1.08), 2)
                orders.append({
                    "orderDate": ts,
                    "totalPrice": gross,
                    "commissionRate": 0.15,  # komisyon -> net ciro analizi için
                })
        return orders

    def normalize(self, raw: list[dict]) -> list[dict]:
        out = []
        for o in raw:
            day = datetime.fromtimestamp(o["orderDate"] / 1000, tz=timezone.utc).date()
            gross = float(o.get("totalPrice", 0) or 0)
            commission = gross * float(o.get("commissionRate", 0) or 0)
            out.append({
                "day": day,
                "channel": "trendyol",
                "revenue": round(gross - commission, 2),  # net ciro (komisyon düşülmüş)
                "orders": 1,
                "sessions": 0,
                "ad_spend": 0.0,
            })
        return out

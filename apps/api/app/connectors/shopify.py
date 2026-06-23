"""Shopify connector.

live  : Admin REST API (X-Shopify-Access-Token). config: {shop, access_token}
sandbox: gerçekçi sahte sipariş üretir (anahtar gerekmez).
"""
import math
import random
from datetime import date, datetime, timedelta

from app.connectors.base import BaseConnector


class ShopifyConnector(BaseConnector):
    kind = "shopify"

    def fetch(self, since: date) -> list[dict]:
        if self.mode == "live":
            return self._fetch_live(since)
        return self._fetch_sandbox(since)

    def _fetch_live(self, since: date) -> list[dict]:
        import httpx
        shop = self.config["shop"]            # ör: my-store.myshopify.com
        token = self.config["access_token"]
        url = f"https://{shop}/admin/api/2024-01/orders.json"
        params = {"status": "any", "created_at_min": since.isoformat(), "limit": 250}
        headers = {"X-Shopify-Access-Token": token}
        with httpx.Client(timeout=30) as c:
            r = c.get(url, params=params, headers=headers)
            r.raise_for_status()
            return r.json().get("orders", [])

    def _fetch_sandbox(self, since: date) -> list[dict]:
        orders = []
        days = (date.today() - since).days + 1
        for i in range(days):
            d = since + timedelta(days=i)
            weekend = 1.3 if d.weekday() >= 5 else 1.0
            n = int((18 + 6 * math.sin(i / 7 * 2 * math.pi)) * weekend * random.uniform(0.9, 1.12))
            for _ in range(max(0, n)):
                price = (40 + (i % 12) + 9.99) * random.uniform(0.92, 1.08)
                orders.append({
                    "created_at": datetime(d.year, d.month, d.day).isoformat(),
                    "total_price": str(round(price, 2)),
                    "source_name": "web",
                })
        return orders

    def normalize(self, raw: list[dict]) -> list[dict]:
        out = []
        for o in raw:
            day = datetime.fromisoformat(o["created_at"].replace("Z", "+00:00")).date()
            out.append({
                "day": day,
                "channel": o.get("source_name", "web"),
                "revenue": float(o.get("total_price", 0) or 0),
                "orders": 1,
                "sessions": 0,   # Shopify orders trafik vermez; GA4 connector tamamlar
                "ad_spend": 0.0,
            })
        return out

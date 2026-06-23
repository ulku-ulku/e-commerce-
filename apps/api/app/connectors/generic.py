"""Katalog-tabanlı jenerik pazaryeri connector'ı.

Katalogdaki herhangi bir pazaryeri için sandbox veri üretir ve TRY'ye normalize eder.
live mode: o pazaryerinin spec'i (base_url/endpoint/mapping) eklendiğinde aktive edilir;
şu an spec'i olmayanlar için anlaşılır bir hata döner.
"""
import math
import random
from datetime import date, datetime, timedelta, timezone

from app.connectors.base import BaseConnector
from app.connectors.catalog import CATALOG_BY_KEY, FX_TO_TRY


class GenericMarketplaceConnector(BaseConnector):
    def __init__(self, org_id, config, mode, entry):
        super().__init__(org_id, config, mode)
        self.entry = entry
        self.kind = entry["key"]          # SalesRecord.source bu değeri kullanır

    def fetch(self, since: date) -> list[dict]:
        if self.mode == "live":
            if not self.entry.get("live_ready"):
                raise RuntimeError(
                    f"{self.entry['label']} için live entegrasyon henüz yok; "
                    f"sandbox modunu kullan veya spec ekle."
                )
            raise RuntimeError(f"{self.entry['label']} live spec'i eklenmeli.")
        return self._fetch_sandbox(since)

    def _fetch_sandbox(self, since: date) -> list[dict]:
        sb = self.entry["sandbox"]
        seed = sum(ord(c) for c in self.kind)   # pazaryeri başına deterministik varyasyon
        days = (date.today() - since).days + 1
        orders = []
        for i in range(days):
            d = since + timedelta(days=i)
            ts = int(datetime(d.year, d.month, d.day, tzinfo=timezone.utc).timestamp() * 1000)
            weekend = 1.35 if d.weekday() >= 5 else 1.0
            wave = 1 + 0.25 * math.sin((i + seed % 7) / 7 * 2 * math.pi)
            # Her senkronde küçük dalgalanma -> gerçek API hissi (sandbox canlanır)
            n = int(sb["daily_orders"] * weekend * wave * random.uniform(0.9, 1.12))
            span = sb["price_max"] - sb["price_min"]
            for j in range(max(0, n)):
                base = sb["price_min"] + ((i * 7 + j * 13 + seed) % 100) / 100 * span
                gross = base * random.uniform(0.92, 1.08)
                orders.append({"ts": ts, "gross": round(gross, 2)})
        return orders

    def normalize(self, raw: list[dict]) -> list[dict]:
        commission = self.entry["sandbox"]["commission"]
        fx = FX_TO_TRY.get(self.entry["currency"], 1.0)
        out = []
        for o in raw:
            day = datetime.fromtimestamp(o["ts"] / 1000, tz=timezone.utc).date()
            net = o["gross"] * (1 - commission) * fx   # komisyon düş + TRY'ye çevir
            out.append({
                "day": day, "channel": self.kind,
                "revenue": round(net, 2), "orders": 1,
                "sessions": 0, "ad_spend": 0.0,
            })
        return out

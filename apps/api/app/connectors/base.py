"""Connector çatısı.

Her platform (Shopify, Trendyol, ...) BaseConnector'dan türer ve iki şey yapar:
  fetch()      -> platformdan ham kayıtları çeker (API veya sandbox)
  normalize()  -> ham kaydı tek 'sales_records' şemasına çevirir

sync() ortak akışı yürütür: fetch -> normalize -> günlük topla -> upsert.
Böylece tüm kaynaklar aynı KPI/AI motoruna akar.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from collections import defaultdict
from datetime import date, timedelta

from sqlalchemy import delete
from sqlalchemy.orm import Session

from app.models import SalesRecord


class BaseConnector(ABC):
    #: data_sources.kind ile eşleşen benzersiz anahtar
    kind: str = "base"

    def __init__(self, org_id: int, config: dict, mode: str = "sandbox"):
        self.org_id = org_id
        self.config = config or {}
        self.mode = mode

    @abstractmethod
    def fetch(self, since: date) -> list[dict]:
        """Platformdan ham sipariş/işlem kayıtlarını döndürür."""

    @abstractmethod
    def normalize(self, raw: list[dict]) -> list[dict]:
        """Ham kayıtları {day, channel, revenue, orders, sessions, ad_spend} listesine çevirir."""

    def sync(self, db: Session, days: int = 30) -> int:
        since = date.today() - timedelta(days=days - 1)
        rows = self.normalize(self.fetch(since))

        # Aynı güne düşen kayıtları topla (gün + kanal kırılımı)
        agg: dict[tuple, dict] = defaultdict(
            lambda: {"revenue": 0.0, "orders": 0, "sessions": 0, "ad_spend": 0.0})
        for r in rows:
            key = (r["day"], r.get("channel", "web"))
            a = agg[key]
            a["revenue"] += r.get("revenue", 0.0)
            a["orders"] += r.get("orders", 0)
            a["sessions"] += r.get("sessions", 0)
            a["ad_spend"] += r.get("ad_spend", 0.0)

        # Idempotent: bu kaynağın senkron penceresindeki eski kayıtlarını temizle
        db.execute(delete(SalesRecord).where(
            SalesRecord.org_id == self.org_id,
            SalesRecord.source == self.kind,
            SalesRecord.day >= since,
        ))

        count = 0
        for (day, channel), v in agg.items():
            db.add(SalesRecord(
                org_id=self.org_id, source=self.kind, day=day, channel=channel,
                revenue=round(v["revenue"], 2), orders=v["orders"],
                sessions=v["sessions"], ad_spend=round(v["ad_spend"], 2),
            ))
            count += 1
        db.commit()
        return count

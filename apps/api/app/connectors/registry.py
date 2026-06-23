"""Connector registry.

Trendyol ve Shopify gerçek live entegrasyonlu CONCRETE sınıflardır.
Diğer tüm pazaryerleri katalogdan GenericMarketplaceConnector ile servis edilir.
Yeni pazaryeri = catalog.py'ye bir satır.
"""
from app.connectors.base import BaseConnector
from app.connectors.catalog import CATALOG_BY_KEY, MARKETPLACES
from app.connectors.generic import GenericMarketplaceConnector
from app.connectors.shopify import ShopifyConnector
from app.connectors.trendyol import TrendyolConnector

# Gerçek API'li özel connector'lar (live_ready)
CONCRETE: dict[str, type[BaseConnector]] = {
    ShopifyConnector.kind: ShopifyConnector,
    TrendyolConnector.kind: TrendyolConnector,
}

# UI/listeleme için tüm desteklenen kaynak anahtarları
SUPPORTED = [m["key"] for m in MARKETPLACES]


def get_connector(kind: str, org_id: int, config: dict, mode: str) -> BaseConnector:
    if kind in CONCRETE:
        return CONCRETE[kind](org_id=org_id, config=config, mode=mode)
    entry = CATALOG_BY_KEY.get(kind)
    if not entry:
        raise ValueError(f"Bilinmeyen kaynak: {kind}")
    return GenericMarketplaceConnector(org_id, config, mode, entry)

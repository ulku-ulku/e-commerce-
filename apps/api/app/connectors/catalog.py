"""Pazaryeri katalogu (yurt içi + yurt dışı).

Yeni pazaryeri eklemek için buraya bir satır eklemek yeterli; jenerik connector
sandbox'ı otomatik üretir. 'live_ready=True' olanlarda gerçek API entegrasyonu vardır;
diğerleri sandbox ile çalışır, live için o platformun spec'i eklenir.

Farklı para birimleri FX_TO_TRY ile TRY tabanına çevrilir (KPI'lar tek para biriminde toplansın).
"""

# Statik kur (prod'da canlı FX servisi: TCMB / exchangerate API ile değiştir)
FX_TO_TRY = {
    "TRY": 1.0, "USD": 34.0, "EUR": 37.0, "GBP": 43.0,
    "PLN": 8.5, "RUB": 0.38, "AED": 9.3,
}


def _m(key, label, region, country, currency, daily_orders, price, commission,
       auth="header_key", live_ready=False):
    return {
        "key": key, "label": label, "region": region, "country": country,
        "currency": currency, "auth": auth, "live_ready": live_ready,
        "sandbox": {"daily_orders": daily_orders, "price_min": price[0],
                    "price_max": price[1], "commission": commission},
    }


MARKETPLACES = [
    # --- Yurt İçi (TR) ---
    _m("trendyol",    "Trendyol",     "tr", "TR", "TRY", 30, (120, 600), 0.15, "basic", live_ready=True),
    _m("hepsiburada", "Hepsiburada",  "tr", "TR", "TRY", 22, (90, 500),  0.13, "basic"),
    _m("n11",         "N11",          "tr", "TR", "TRY", 14, (70, 400),  0.12),
    _m("ciceksepeti", "Çiçeksepeti",  "tr", "TR", "TRY", 10, (150, 700), 0.14),
    _m("pazarama",    "Pazarama",     "tr", "TR", "TRY", 7,  (80, 350),  0.11),
    _m("pttavm",      "PTT AVM",      "tr", "TR", "TRY", 6,  (60, 300),  0.10),
    _m("amazon_tr",   "Amazon TR",    "tr", "TR", "TRY", 18, (100, 550), 0.15),

    # --- Yurt Dışı / Global ---
    _m("shopify",     "Shopify",      "global", "GLOBAL", "USD", 18, (40, 120),  0.0,  "bearer", live_ready=True),
    _m("amazon",      "Amazon (Global)", "global", "US", "USD", 35, (15, 90),   0.15, "oauth"),
    _m("ebay",        "eBay",         "global", "US", "USD", 20, (20, 150),  0.12, "oauth"),
    _m("etsy",        "Etsy",         "global", "US", "USD", 12, (18, 80),   0.065, "oauth"),
    _m("aliexpress",  "AliExpress",   "global", "CN", "USD", 25, (5, 60),    0.08),
    _m("walmart",     "Walmart",      "global", "US", "USD", 16, (25, 120),  0.15),
    _m("allegro",     "Allegro",      "global", "PL", "PLN", 14, (40, 300),  0.10, "oauth"),
    _m("cdiscount",   "Cdiscount",    "global", "FR", "EUR", 9,  (20, 150),  0.13),
    _m("noon",        "Noon",         "global", "AE", "AED", 11, (50, 400),  0.12),
    _m("ozon",        "Ozon",         "global", "RU", "RUB", 13, (500, 4000), 0.13),
]

CATALOG_BY_KEY = {m["key"]: m for m in MARKETPLACES}

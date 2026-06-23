"""Reklam kampanyası + trafik hunisi örnek verisi: python -m app.seed_marketing
Domain 4 (huni) ve 5 (reklam) motorlarını besler. Darboğaz bilinçli olarak ödeme sayfasında.
"""
import random
from datetime import date, timedelta

from app.core.database import Base, SessionLocal, engine
from app.models import AdCampaign, FunnelDaily, Organization

# (isim, platform, harcama, gösterim, tık, dönüşüm, ciro, yeni_müşteri)
CAMPAIGNS = [
    ("Marka Bilinirliği - Meta", "meta",   45000, 1200000, 18000, 210, 38000,  150),  # ROAS<1 KAPAT
    ("Retargeting - Meta",       "meta",   22000, 380000,  14000, 520, 121000, 90),   # iyi
    ("Google Shopping",          "google", 38000, 520000,  21000, 640, 152000, 280),  # iyi
    ("Brand Search - Google",    "google", 9000,  90000,   8500,  410, 98000,  60),   # ölçekle
    ("TikTok Video",             "tiktok", 31000, 950000,  27000, 240, 41000,  200),  # düşük verim
    ("Prospecting - Meta",       "meta",   52000, 1500000, 19000, 180, 33000,  170),  # ROAS<1 KAPAT
    ("E-posta + SMS",            "google", 4000,  0,       6000,  380, 142000, 20),   # ölçekle
]


def _seed_campaigns(db, org):
    if db.query(AdCampaign).filter(AdCampaign.org_id == org.id).first():
        return 0
    start = date.today() - timedelta(days=30)
    for name, plat, spend, imp, clk, conv, rev, newc in CAMPAIGNS:
        roas = rev / spend if spend else 0
        db.add(AdCampaign(
            org_id=org.id, name=name, platform=plat,
            status="paused" if roas < 1 else "active",
            start_date=start, spend=spend, impressions=imp, clicks=clk,
            conversions=conv, revenue=rev, new_customers=newc,
        ))
    return len(CAMPAIGNS)


def _seed_funnel(db, org):
    if db.query(FunnelDaily).filter(FunnelDaily.org_id == org.id).first():
        return 0
    rnd = random.Random(7)
    n = 0
    for off in range(30):
        d = date.today() - timedelta(days=29 - off)
        for ch in ("web", "trendyol"):
            visitors = int(rnd.uniform(900, 1400) * (1.3 if d.weekday() >= 5 else 1.0))
            product_views = int(visitors * rnd.uniform(0.62, 0.70))    # iyi
            add_to_cart = int(product_views * rnd.uniform(0.38, 0.44))  # iyi
            checkout = int(add_to_cart * rnd.uniform(0.60, 0.68))       # normal
            purchases = int(checkout * rnd.uniform(0.24, 0.30))         # DARBOĞAZ (ödeme sayfası)
            db.add(FunnelDaily(
                org_id=org.id, day=d, channel=ch, visitors=visitors,
                product_views=product_views, add_to_cart=add_to_cart,
                checkout_started=checkout, purchases=purchases,
            ))
            n += 1
    return n


def run():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        org = db.query(Organization).first()
        if not org:
            print("Önce app.seed çalıştır.")
            return
        c = _seed_campaigns(db, org)
        f = _seed_funnel(db, org)
        db.commit()
        print(f"[OK] Pazarlama verisi: {c} kampanya, {f} gün-kanal huni kaydı")
    finally:
        db.close()


if __name__ == "__main__":
    run()

"""SKU/müşteri/sipariş kalemi örnek verisi: python -m app.seed_analytics
Kârlılık + Karar Skoru motorlarını beslemek için gerçekçi (bazıları bilinçli zararlı) SKU'lar.
"""
import random
from datetime import date, timedelta

from app.core.database import Base, SessionLocal, engine
from app.models import Customer, OrderItem, Organization, Product

CATEGORIES = ["Elektronik", "Giyim", "Kozmetik", "Ev & Yaşam", "Spor", "Aksesuar"]
CITIES = ["İstanbul", "Ankara", "İzmir", "Bursa", "Antalya", "Adana"]
CHANNELS = ["web", "trendyol", "hepsiburada", "amazon"]

# (isim, kategori, fiyat, birim_maliyet, paketleme, stok, tedarik_gün, talep/gün, komisyon%, reklam/sipariş)
SKU_SPECS = [
    ("Kablosuz Kulaklık",   "Elektronik", 899, 540, 25, 120, 21, 12, 0.15, 35),
    ("Powerbank 20000",     "Elektronik", 549, 410, 20, 40,  21, 9,  0.15, 28),  # düşük marj + stok riski
    ("Akıllı Saat",         "Elektronik", 1499, 950, 30, 200, 28, 7,  0.15, 60),
    ("Oversize T-Shirt",    "Giyim",      299, 95,  15, 500, 10, 20, 0.18, 18),  # yıldız
    ("Mevsimlik Mont",      "Giyim",      1299, 1180, 25, 60, 30, 6,  0.18, 90), # ZARARDA ama satıyor
    ("Spor Tayt",           "Giyim",      399, 150, 12, 300, 14, 14, 0.18, 22),
    ("Nemlendirici Krem",   "Kozmetik",   249, 88,  10, 400, 14, 18, 0.14, 15),  # yıldız
    ("Parfüm 50ml",         "Kozmetik",   799, 690, 18, 80,  21, 8,  0.14, 70),  # düşük marj + reklam israfı
    ("Vitamin C Serum",     "Kozmetik",   349, 130, 10, 250, 14, 11, 0.14, 20),
    ("Bambu Saklama Seti",  "Ev & Yaşam", 459, 210, 30, 150, 18, 9,  0.16, 25),
    ("Aroma Mum",           "Ev & Yaşam", 199, 175, 14, 90,  14, 16, 0.16, 30),  # ZARARDA ama satıyor
    ("Yoga Matı",           "Spor",       399, 160, 20, 70,  20, 10, 0.17, 24),
    ("Dambıl Seti 10kg",    "Spor",       699, 520, 40, 25,  28, 5,  0.17, 35),  # stok riski
    ("Deri Cüzdan",         "Aksesuar",   349, 120, 12, 220, 18, 13, 0.16, 19),
    ("Güneş Gözlüğü",       "Aksesuar",   499, 175, 15, 180, 21, 12, 0.16, 40),
]


def run():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        org = db.query(Organization).first()
        if not org:
            print("Önce app.seed çalıştır (org/kullanıcı yok).")
            return
        if db.query(Product).filter(Product.org_id == org.id).first():
            print("Analytics verisi zaten mevcut.")
            return

        rnd = random.Random(42)  # tekrarlanabilir

        # --- Ürünler ---
        products = []
        for i, (name, cat, price, cost, pack, stock, lead, dpd, comm, adpo) in enumerate(SKU_SPECS):
            sku = f"SKU-{1000 + i}"
            comp = round(price * rnd.uniform(0.9, 1.12), 2)  # rakip fiyat
            p = Product(org_id=org.id, sku=sku, name=name, category=cat, price=price,
                        unit_cost=cost, packaging_cost=pack, stock=stock,
                        lead_time_days=lead, competitor_price=comp)
            db.add(p)
            products.append((p, dpd, comm, adpo))

        # --- Müşteriler ---
        customers = []
        for c in range(400):
            first = date.today() - timedelta(days=rnd.randint(0, 180))
            oc = rnd.choices([1, 2, 3, 5, 9], weights=[55, 22, 13, 7, 3])[0]
            seg = ("vip" if oc >= 5 else "repeat" if oc >= 2 else "new")
            last = date.today() - timedelta(days=rnd.randint(0, 90))
            if oc == 1 and (date.today() - last).days > 60:
                seg = "at_risk"
            cust = Customer(org_id=org.id, external_id=f"C{c:04d}", first_order_date=first,
                            last_order_date=last, city=rnd.choice(CITIES), segment=seg,
                            orders_count=oc, ltv=0.0)
            db.add(cust)
            customers.append(cust)
        db.flush()  # id almak için

        # --- Sipariş kalemleri (60 gün) ---
        order_no = 0
        for day_off in range(60):
            d = date.today() - timedelta(days=59 - day_off)
            weekend = 1.35 if d.weekday() >= 5 else 1.0
            for (p, dpd, comm, adpo) in products:
                n = int(dpd * weekend * rnd.uniform(0.7, 1.3))
                for _ in range(n):
                    order_no += 1
                    cust = rnd.choice(customers)
                    qty = rnd.choices([1, 2, 3], weights=[75, 18, 7])[0]
                    disc = round(p.price * qty * rnd.choice([0, 0, 0.1, 0.15]), 2)
                    net = round(p.price * qty - disc, 2)
                    ch = rnd.choice(CHANNELS)
                    commission = round(net * (comm if ch != "web" else 0.0), 2)
                    returned = rnd.random() < 0.05
                    cust.ltv += net
                    db.add(OrderItem(
                        org_id=org.id, order_external_id=f"ORD{order_no:06d}",
                        customer_id=cust.id, day=d, channel=ch, sku=p.sku, category=p.category,
                        qty=qty, unit_price=p.price, discount=disc, net_sales=net,
                        shipping_cost=round(rnd.uniform(20, 45), 2), commission=commission,
                        ad_cost=round(adpo * rnd.uniform(0.6, 1.4), 2), returned=returned,
                    ))
            if day_off % 15 == 0:
                db.commit()
        db.commit()
        print(f"[OK] Analytics verisi: {len(products)} SKU, {len(customers)} musteri, {order_no} siparis kalemi")
    finally:
        db.close()


if __name__ == "__main__":
    run()

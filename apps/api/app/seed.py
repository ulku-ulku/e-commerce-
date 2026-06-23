"""Demo veri tohumlama: python -m app.seed
login: demo@commerce.ai / demo1234"""
import math
from datetime import date, timedelta

from app.core.database import Base, SessionLocal, engine
from app.core.security import hash_password
from app.models import Organization, User, SalesRecord


def run():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        if db.query(User).filter(User.email == "demo@commerce.ai").first():
            print("Demo zaten mevcut.")
            return

        org = Organization(name="Demo Store")
        db.add(org)
        db.flush()
        db.add(User(org_id=org.id, email="demo@commerce.ai",
                    hashed_password=hash_password("demo1234"), role="owner"))

        today = date.today()
        # Deterministik sentetik veri: trend + haftalık mevsimsellik + reklam
        for i in range(60):
            d = today - timedelta(days=59 - i)
            seasonal = 1 + 0.25 * math.sin(i / 7 * 2 * math.pi)
            weekend = 1.3 if d.weekday() >= 5 else 1.0
            trend = 1 + i * 0.012
            sessions = int(800 * seasonal * weekend * trend)
            orders = int(sessions * 0.022)
            revenue = round(orders * (45 + (i % 10)), 2)
            ad_spend = round(revenue * 0.18, 2)
            db.add(SalesRecord(
                org_id=org.id, source="csv", day=d, channel="web",
                revenue=revenue, orders=orders, sessions=sessions, ad_spend=ad_spend,
            ))

        db.commit()
        print("[OK] Demo olusturuldu: demo@commerce.ai / demo1234 (60 gun veri)")
    finally:
        db.close()


if __name__ == "__main__":
    run()

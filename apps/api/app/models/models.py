from datetime import datetime, date

from sqlalchemy import (
    String, Integer, Float, Boolean, ForeignKey, DateTime, Date, Text, func, Index,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Organization(Base):
    __tablename__ = "organizations"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    users: Mapped[list["User"]] = relationship(back_populates="org")


class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    org_id: Mapped[int] = mapped_column(ForeignKey("organizations.id"))
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(20), default="owner")  # owner|admin|analyst
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    org: Mapped["Organization"] = relationship(back_populates="users")


class DataSource(Base):
    __tablename__ = "data_sources"
    id: Mapped[int] = mapped_column(primary_key=True)
    org_id: Mapped[int] = mapped_column(ForeignKey("organizations.id"), index=True)
    kind: Mapped[str] = mapped_column(String(30))  # shopify|trendyol|hepsiburada|meta_ads|ga4|csv
    status: Mapped[str] = mapped_column(String(20), default="connected")
    mode: Mapped[str] = mapped_column(String(20), default="sandbox")  # sandbox|live
    config: Mapped[str] = mapped_column(Text, default="{}")  # kimlik bilgileri (JSON)
    last_synced_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class SalesRecord(Base):
    """Tüm kaynaklardan gelen veriyi normalize eden tek 'fact' tablosu."""
    __tablename__ = "sales_records"
    id: Mapped[int] = mapped_column(primary_key=True)
    org_id: Mapped[int] = mapped_column(ForeignKey("organizations.id"), index=True)
    source: Mapped[str] = mapped_column(String(30), default="csv")
    day: Mapped[date] = mapped_column(Date, index=True)
    channel: Mapped[str] = mapped_column(String(40), default="web")
    revenue: Mapped[float] = mapped_column(Float, default=0.0)
    orders: Mapped[int] = mapped_column(Integer, default=0)
    sessions: Mapped[int] = mapped_column(Integer, default=0)
    ad_spend: Mapped[float] = mapped_column(Float, default=0.0)

    __table_args__ = (Index("ix_org_day", "org_id", "day"),)


class Product(Base):
    """SKU ana kaydı — kârlılık ve stok analizinin kalbi (maliyet yapısı + operasyon)."""
    __tablename__ = "products"
    id: Mapped[int] = mapped_column(primary_key=True)
    org_id: Mapped[int] = mapped_column(ForeignKey("organizations.id"), index=True)
    sku: Mapped[str] = mapped_column(String(60), index=True)
    name: Mapped[str] = mapped_column(String(160))
    category: Mapped[str] = mapped_column(String(60), index=True)
    price: Mapped[float] = mapped_column(Float, default=0.0)          # liste fiyatı
    # Maliyet yapısı (domain 2)
    unit_cost: Mapped[float] = mapped_column(Float, default=0.0)      # ürün maliyeti
    packaging_cost: Mapped[float] = mapped_column(Float, default=0.0)  # paketleme
    # Operasyon (domain 6)
    stock: Mapped[int] = mapped_column(Integer, default=0)
    lead_time_days: Mapped[int] = mapped_column(Integer, default=14)  # tedarik süresi
    # Pazar (domain 7)
    competitor_price: Mapped[float | None] = mapped_column(Float, nullable=True)


class Customer(Base):
    """Müşteri (domain 3) — LTV, tekrar, terk riski."""
    __tablename__ = "customers"
    id: Mapped[int] = mapped_column(primary_key=True)
    org_id: Mapped[int] = mapped_column(ForeignKey("organizations.id"), index=True)
    external_id: Mapped[str] = mapped_column(String(60), index=True)
    first_order_date: Mapped[date] = mapped_column(Date)
    last_order_date: Mapped[date] = mapped_column(Date)
    city: Mapped[str] = mapped_column(String(40), default="İstanbul")
    segment: Mapped[str] = mapped_column(String(20), default="new")  # new|repeat|vip|at_risk
    orders_count: Mapped[int] = mapped_column(Integer, default=0)
    ltv: Mapped[float] = mapped_column(Float, default=0.0)            # yaşam boyu değer


class OrderItem(Base):
    """Satış satır kalemi (domain 1) — tüm analizlerin atomik verisi."""
    __tablename__ = "order_items"
    id: Mapped[int] = mapped_column(primary_key=True)
    org_id: Mapped[int] = mapped_column(ForeignKey("organizations.id"), index=True)
    order_external_id: Mapped[str] = mapped_column(String(60), index=True)
    customer_id: Mapped[int | None] = mapped_column(ForeignKey("customers.id"), nullable=True)
    day: Mapped[date] = mapped_column(Date, index=True)
    channel: Mapped[str] = mapped_column(String(40), default="web")
    sku: Mapped[str] = mapped_column(String(60), index=True)
    category: Mapped[str] = mapped_column(String(60))
    qty: Mapped[int] = mapped_column(Integer, default=1)
    unit_price: Mapped[float] = mapped_column(Float, default=0.0)
    discount: Mapped[float] = mapped_column(Float, default=0.0)
    net_sales: Mapped[float] = mapped_column(Float, default=0.0)      # (fiyat*adet) - indirim
    # Sipariş başı dağıtılan maliyetler (domain 2)
    shipping_cost: Mapped[float] = mapped_column(Float, default=0.0)
    commission: Mapped[float] = mapped_column(Float, default=0.0)
    ad_cost: Mapped[float] = mapped_column(Float, default=0.0)
    returned: Mapped[bool] = mapped_column(Boolean, default=False)

    __table_args__ = (Index("ix_oi_org_sku_day", "org_id", "sku", "day"),)


class AdCampaign(Base):
    """Reklam kampanyası (domain 5) — ROAS, CAC, payback kaynağı."""
    __tablename__ = "ad_campaigns"
    id: Mapped[int] = mapped_column(primary_key=True)
    org_id: Mapped[int] = mapped_column(ForeignKey("organizations.id"), index=True)
    name: Mapped[str] = mapped_column(String(120))
    platform: Mapped[str] = mapped_column(String(30), default="meta")  # meta|google|tiktok
    status: Mapped[str] = mapped_column(String(20), default="active")  # active|paused
    start_date: Mapped[date] = mapped_column(Date)
    spend: Mapped[float] = mapped_column(Float, default=0.0)
    impressions: Mapped[int] = mapped_column(Integer, default=0)
    clicks: Mapped[int] = mapped_column(Integer, default=0)
    conversions: Mapped[int] = mapped_column(Integer, default=0)       # sipariş
    revenue: Mapped[float] = mapped_column(Float, default=0.0)         # atfedilen ciro
    new_customers: Mapped[int] = mapped_column(Integer, default=0)


class FunnelDaily(Base):
    """Trafik & dönüşüm hunisi (domain 4) — günlük aşama sayıları."""
    __tablename__ = "funnel_daily"
    id: Mapped[int] = mapped_column(primary_key=True)
    org_id: Mapped[int] = mapped_column(ForeignKey("organizations.id"), index=True)
    day: Mapped[date] = mapped_column(Date, index=True)
    channel: Mapped[str] = mapped_column(String(40), default="web")
    visitors: Mapped[int] = mapped_column(Integer, default=0)
    product_views: Mapped[int] = mapped_column(Integer, default=0)
    add_to_cart: Mapped[int] = mapped_column(Integer, default=0)
    checkout_started: Mapped[int] = mapped_column(Integer, default=0)
    purchases: Mapped[int] = mapped_column(Integer, default=0)


class DecisionLog(Base):
    """Karar→Sonuç geri-besleme (kapalı döngü).
    Aksiyon kabul edilince taban metrik fotoğraflanır; sonra ölçülüp etki görülür."""
    __tablename__ = "decision_logs"
    id: Mapped[int] = mapped_column(primary_key=True)
    org_id: Mapped[int] = mapped_column(ForeignKey("organizations.id"), index=True)
    title: Mapped[str] = mapped_column(String(255))
    domain: Mapped[str] = mapped_column(String(40))
    impact_estimate: Mapped[float] = mapped_column(Float, default=0.0)
    status: Mapped[str] = mapped_column(String(20), default="applied")  # applied|executed|planned|measured
    change_note: Mapped[str | None] = mapped_column(String(255), nullable=True)  # before→after
    baseline_metric: Mapped[str] = mapped_column(String(40), default="total_profit")
    baseline_value: Mapped[float] = mapped_column(Float, default=0.0)
    outcome_value: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class Insight(Base):
    __tablename__ = "insights"
    id: Mapped[int] = mapped_column(primary_key=True)
    org_id: Mapped[int] = mapped_column(ForeignKey("organizations.id"), index=True)
    kind: Mapped[str] = mapped_column(String(30), default="weekly")  # weekly|alert|forecast
    title: Mapped[str] = mapped_column(String(255))
    body: Mapped[str] = mapped_column(Text)
    severity: Mapped[str] = mapped_column(String(20), default="info")  # info|warning|critical
    actions: Mapped[str] = mapped_column(Text, default="[]")  # JSON list of recommended actions
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

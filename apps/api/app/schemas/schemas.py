from datetime import datetime, date
from pydantic import BaseModel, EmailStr


# --- Auth ---
class RegisterIn(BaseModel):
    email: EmailStr
    password: str
    org_name: str


class LoginIn(BaseModel):
    email: EmailStr
    password: str


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserOut(BaseModel):
    id: int
    email: str
    role: str
    org_id: int

    class Config:
        from_attributes = True


# --- KPI ---
class KpiSummary(BaseModel):
    revenue: float
    orders: int
    sessions: int
    ad_spend: float
    aov: float          # average order value
    conversion_rate: float
    roas: float         # return on ad spend
    revenue_delta_pct: float  # vs önceki dönem


class TimePoint(BaseModel):
    day: date
    revenue: float
    orders: int


class ForecastPoint(BaseModel):
    day: date
    predicted_revenue: float


# --- Insights ---
class InsightOut(BaseModel):
    id: int
    kind: str
    title: str
    body: str
    severity: str
    actions: list[dict]
    created_at: datetime

    class Config:
        from_attributes = True


class IngestResult(BaseModel):
    rows_ingested: int
    source: str

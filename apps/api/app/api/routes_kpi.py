from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models import User
from app.schemas.schemas import ForecastPoint, KpiSummary, TimePoint
from app.services.forecast import forecast_revenue
from app.services.kpi_engine import kpi_summary, timeseries

router = APIRouter(prefix="/api/kpi", tags=["kpi"])


@router.get("/summary", response_model=KpiSummary)
def summary(days: int = 30, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return kpi_summary(db, user.org_id, days)


@router.get("/timeseries", response_model=list[TimePoint])
def series(days: int = 30, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return timeseries(db, user.org_id, days)


@router.get("/forecast", response_model=list[ForecastPoint])
def forecast(horizon: int = 14, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return forecast_revenue(db, user.org_id, horizon)

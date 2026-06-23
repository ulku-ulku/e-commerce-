import json

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models import Insight, User
from app.schemas.schemas import InsightOut
from app.services.ai_insights import generate_insight
from app.services.decision_engine import evaluate
from app.services.forecast import forecast_revenue
from app.services.kpi_engine import kpi_summary

router = APIRouter(prefix="/api/insights", tags=["insights"])


def _to_out(ins: Insight) -> dict:
    return {
        "id": ins.id, "kind": ins.kind, "title": ins.title, "body": ins.body,
        "severity": ins.severity, "actions": json.loads(ins.actions or "[]"),
        "created_at": ins.created_at,
    }


@router.get("", response_model=list[InsightOut])
def list_insights(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    rows = (db.query(Insight).filter(Insight.org_id == user.org_id)
            .order_by(Insight.created_at.desc()).limit(20).all())
    return [_to_out(r) for r in rows]


@router.post("/generate", response_model=InsightOut)
def generate(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """Senkron üretim (MVP). Ağır işler için /generate-async + worker kullanılabilir."""
    kpi = kpi_summary(db, user.org_id)
    fc = forecast_revenue(db, user.org_id)
    signals = evaluate(kpi, fc)
    result = generate_insight(kpi, fc, signals)

    ins = Insight(
        org_id=user.org_id, kind="weekly",
        title=result["title"][:255], body=result["body"],
        severity=result.get("severity", "info"),
        actions=json.dumps(result.get("actions", []), ensure_ascii=False),
    )
    db.add(ins)
    db.commit()
    db.refresh(ins)
    return _to_out(ins)

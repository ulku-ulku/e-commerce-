from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models import DecisionLog, User
from app.services.action_queue import build_queue
from app.services.executor import execute as execute_action
from app.services.ad_engine import campaign_metrics
from app.services.customer_analytics import customer_overview
from app.services.decision_score import decision_scores
from app.services.elasticity import pricing_recommendations, simulate_one
from app.services.funnel import funnel_analysis
from app.services.growth import growth_analysis
from app.services.profitability import sku_profitability

router = APIRouter(prefix="/api/analytics", tags=["analytics"])


def _total_profit(db: Session, org_id: int) -> float:
    return decision_scores(db, org_id)["summary"].get("total_profit", 0.0)


@router.get("/sku-profitability")
def sku_profit(days: int = 30, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return sku_profitability(db, user.org_id, days)


@router.get("/decision-scores")
def decisions(days: int = 30, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return decision_scores(db, user.org_id, days)


@router.get("/ads")
def ads(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return campaign_metrics(db, user.org_id)


@router.get("/customers")
def customers(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return customer_overview(db, user.org_id)


@router.get("/funnel")
def funnel(days: int = 30, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return funnel_analysis(db, user.org_id, days)


@router.get("/growth")
def growth(period: str = "week", db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return growth_analysis(db, user.org_id, days=30 if period == "month" else 7)


# ---------- Fiyat elastikiyeti & simülasyon (domain 7) ----------
@router.get("/pricing")
def pricing(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return pricing_recommendations(db, user.org_id)


class SimulateIn(BaseModel):
    sku: str
    price_change_pct: float


@router.post("/pricing/simulate")
def simulate(data: SimulateIn, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return simulate_one(db, user.org_id, data.sku, data.price_change_pct)


# ---------- Aksiyon Kuyruğu ----------
@router.get("/action-queue")
def action_queue(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return build_queue(db, user.org_id)


# ---------- Karar→Sonuç geri-besleme ----------
class ApplyIn(BaseModel):
    title: str
    domain: str
    impact_estimate: float = 0.0


@router.post("/decisions/apply")
def apply_decision(data: ApplyIn, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    log = DecisionLog(
        org_id=user.org_id, title=data.title, domain=data.domain,
        impact_estimate=data.impact_estimate, status="applied",
        baseline_metric="total_profit", baseline_value=_total_profit(db, user.org_id),
    )
    db.add(log)
    db.commit()
    db.refresh(log)
    return {"id": log.id, "status": log.status, "baseline_value": log.baseline_value}


# ---------- #4 Agency: aksiyonu GERÇEKTEN uygula (guardrail'li) ----------
class ExecuteIn(BaseModel):
    title: str
    domain: str
    impact_estimate: float = 0.0
    requires_confirm: bool = False
    confirm: bool = False
    exec: dict  # {type, target, params, auto}


@router.post("/actions/execute")
def execute_decision(data: ExecuteIn, db: Session = Depends(get_db),
                     user: User = Depends(get_current_user)):
    # Guardrail: riskli aksiyon onaysız çalıştırılamaz
    if data.requires_confirm and not data.confirm:
        return {"needs_confirm": True,
                "preview": f"'{data.title}' uygulanacak (tahmini etki {data.impact_estimate:,.0f}₺). Onayla."}

    baseline = _total_profit(db, user.org_id)
    result = execute_action(db, user.org_id, data.exec)
    status = "planned" if result.get("manual") else ("executed" if result.get("ok") else "applied")

    log = DecisionLog(
        org_id=user.org_id, title=data.title, domain=data.domain,
        impact_estimate=data.impact_estimate, status=status,
        change_note=result.get("change"), baseline_metric="total_profit",
        baseline_value=baseline,
    )
    db.add(log)
    db.commit()
    db.refresh(log)
    return {"id": log.id, "status": status, "ok": result.get("ok"),
            "change": result.get("change")}


@router.post("/decisions/{log_id}/measure")
def measure_decision(log_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    log = db.query(DecisionLog).filter(
        DecisionLog.id == log_id, DecisionLog.org_id == user.org_id).first()
    if not log:
        raise HTTPException(404, "Karar kaydı bulunamadı")
    log.outcome_value = _total_profit(db, user.org_id)
    log.status = "measured"
    log.resolved_at = datetime.utcnow()
    db.commit()
    return {"id": log.id, "delta": round(log.outcome_value - log.baseline_value, 2)}


@router.get("/decisions")
def list_decisions(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    rows = db.query(DecisionLog).filter(DecisionLog.org_id == user.org_id).order_by(
        DecisionLog.created_at.desc()).limit(30).all()
    return [{
        "id": r.id, "title": r.title, "domain": r.domain, "status": r.status,
        "change_note": r.change_note,
        "impact_estimate": r.impact_estimate, "baseline_value": r.baseline_value,
        "outcome_value": r.outcome_value,
        "delta": round((r.outcome_value - r.baseline_value), 2) if r.outcome_value is not None else None,
        "created_at": str(r.created_at),
    } for r in rows]

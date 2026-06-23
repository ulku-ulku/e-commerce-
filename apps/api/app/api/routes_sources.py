"""Veri kaynağı yönetimi: bağlan, listele, senkronize et."""
import json
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.database import get_db
from app.connectors.catalog import MARKETPLACES
from app.connectors.registry import SUPPORTED, get_connector
from app.models import DataSource, User
from app.services import scheduler

router = APIRouter(prefix="/api/sources", tags=["sources"])


class ConnectIn(BaseModel):
    kind: str                       # shopify | trendyol
    mode: str = "sandbox"           # sandbox | live
    config: dict = {}               # live modda kimlik bilgileri


class SourceOut(BaseModel):
    id: int
    kind: str
    mode: str
    status: str
    last_synced_at: datetime | None


class SyncResult(BaseModel):
    source_id: int
    kind: str
    rows_ingested: int


class AutoSyncIn(BaseModel):
    enabled: bool
    minutes: int = 1


@router.get("/auto-sync")
def auto_sync_status(user: User = Depends(get_current_user)):
    return scheduler.get_state()


@router.post("/auto-sync")
def auto_sync_set(data: AutoSyncIn, user: User = Depends(get_current_user)):
    return scheduler.set_state(data.enabled, data.minutes)


@router.get("/catalog")
def catalog():
    """UI için tüm desteklenen pazaryerleri (yurt içi + yurt dışı) metadata'sı."""
    return {"marketplaces": [
        {k: m[k] for k in ("key", "label", "region", "country", "currency", "live_ready")}
        for m in MARKETPLACES
    ]}


@router.get("", response_model=list[SourceOut])
def list_sources(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return db.query(DataSource).filter(DataSource.org_id == user.org_id).all()


@router.post("/connect", response_model=SourceOut)
def connect(data: ConnectIn, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    if data.kind not in SUPPORTED:
        raise HTTPException(400, f"Desteklenmeyen kaynak: {data.kind}")

    ds = db.query(DataSource).filter(
        DataSource.org_id == user.org_id, DataSource.kind == data.kind).first()
    if not ds:
        ds = DataSource(org_id=user.org_id, kind=data.kind)
        db.add(ds)
    ds.mode = data.mode
    ds.config = json.dumps(data.config)
    ds.status = "connected"
    db.commit()
    db.refresh(ds)
    return ds


class ConnectAllIn(BaseModel):
    region: str | None = None   # "tr" | "global" | None(hepsi)
    mode: str = "sandbox"


@router.post("/connect-all")
def connect_all(data: ConnectAllIn, db: Session = Depends(get_db),
                user: User = Depends(get_current_user)):
    """Seçilen bölgedeki tüm pazaryerlerini bağlar + senkronize eder (sandbox)."""
    targets = [m for m in MARKETPLACES if data.region in (None, m["region"])]
    results = []
    for m in targets:
        ds = db.query(DataSource).filter(
            DataSource.org_id == user.org_id, DataSource.kind == m["key"]).first()
        if not ds:
            ds = DataSource(org_id=user.org_id, kind=m["key"])
            db.add(ds)
        ds.mode = data.mode
        ds.config = "{}"
        db.flush()
        try:
            count = get_connector(m["key"], user.org_id, {}, data.mode).sync(db, days=30)
            ds.status = "connected"
            ds.last_synced_at = datetime.utcnow()
            results.append({"kind": m["key"], "rows_ingested": count})
        except Exception as e:
            ds.status = "error"
            results.append({"kind": m["key"], "error": str(e)})
    db.commit()
    return {"synced": results, "total_sources": len(results)}


@router.post("/{source_id}/sync", response_model=SyncResult)
def sync(source_id: int, days: int = 30, db: Session = Depends(get_db),
         user: User = Depends(get_current_user)):
    ds = db.query(DataSource).filter(
        DataSource.id == source_id, DataSource.org_id == user.org_id).first()
    if not ds:
        raise HTTPException(404, "Kaynak bulunamadı")

    connector = get_connector(ds.kind, user.org_id, json.loads(ds.config or "{}"), ds.mode)
    try:
        count = connector.sync(db, days=days)
    except Exception as e:
        ds.status = "error"
        db.commit()
        raise HTTPException(502, f"Senkron hatası ({ds.kind}): {e}")

    ds.status = "connected"
    ds.last_synced_at = datetime.utcnow()
    db.commit()
    return SyncResult(source_id=ds.id, kind=ds.kind, rows_ingested=count)

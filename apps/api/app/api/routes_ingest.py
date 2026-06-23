"""Veri alımı — evrensel/akıllı CSV + Excel içe aktarma.

Her e-ticaret dosyasını kabul eder (CSV veya .xlsx): günlük ciro VEYA sipariş/işlem satırı.
Kolonlar esnek tanınır (TR+EN), satır-seviyesi otomatik güne toplanır.
Detaylar: app/services/smart_ingest.py
"""
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models import DataSource, User
from app.services.smart_ingest import smart_ingest

router = APIRouter(prefix="/api/ingest", tags=["ingest"])


@router.post("/csv")
async def ingest_csv(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    raw = await file.read()
    try:
        result = smart_ingest(db, user.org_id, raw, filename=file.filename or "")
    except ValueError as e:
        raise HTTPException(400, str(e))
    except Exception as e:
        raise HTTPException(400, f"CSV işlenemedi: {e}")

    ds = db.query(DataSource).filter(
        DataSource.org_id == user.org_id, DataSource.kind == "csv").first()
    if not ds:
        ds = DataSource(org_id=user.org_id, kind="csv")
        db.add(ds)
    from datetime import datetime
    ds.last_synced_at = datetime.utcnow()
    db.commit()
    return result

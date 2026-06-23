"""Otomatik & anlık senkron — arka plan zamanlayıcı (thread).

Açıkken her N dakikada bağlı tüm kaynakları otomatik senkronize eder; elle
tetiklemeye gerek kalmaz. Redis gerektirmez (yerel/Docker'sız ortam için).
"""
import json
import threading
import time
from datetime import datetime

from app.connectors.registry import get_connector
from app.core.database import SessionLocal
from app.models import DataSource

_state = {"enabled": False, "minutes": 1, "last_run": None, "next_run": None, "last_synced": 0}
_lock = threading.Lock()
_started = False


def get_state() -> dict:
    return dict(_state)


def set_state(enabled: bool, minutes: int) -> dict:
    with _lock:
        _state["enabled"] = bool(enabled)
        _state["minutes"] = max(1, int(minutes))
        _state["next_run"] = None if not enabled else _state["next_run"]
    return get_state()


def _run_once():
    db = SessionLocal()
    try:
        sources = db.query(DataSource).filter(DataSource.kind != "csv").all()
        n = 0
        for ds in sources:
            try:
                conn = get_connector(ds.kind, ds.org_id, json.loads(ds.config or "{}"), ds.mode)
                conn.sync(db, days=30)
                ds.last_synced_at = datetime.utcnow()
                ds.status = "connected"
                n += 1
            except Exception:
                continue
        db.commit()
        _state["last_synced"] = n
        _state["last_run"] = datetime.utcnow().isoformat()
    except Exception:
        pass
    finally:
        db.close()


def _loop():
    last = 0.0
    while True:
        try:
            if _state["enabled"]:
                now = time.monotonic()
                if now - last >= _state["minutes"] * 60:
                    _run_once()
                    last = time.monotonic()
        except Exception:
            pass
        time.sleep(5)


def start():
    global _started
    if _started:
        return
    _started = True
    threading.Thread(target=_loop, daemon=True, name="auto-sync").start()

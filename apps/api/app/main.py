from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.database import Base, engine
from app.api import (
    routes_auth, routes_ingest, routes_kpi, routes_insights, routes_sources, routes_analytics,
    routes_assistant,
)
import app.models  # noqa: F401  (modellerin Base'e kaydı için)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # MVP: tabloları oto-oluştur. Prod'da Alembic migration kullan.
    Base.metadata.create_all(bind=engine)
    from app.services import scheduler
    scheduler.start()  # otomatik senkron thread'i (varsayılan kapalı)
    yield


app = FastAPI(title="Commerce-AI API", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health():
    return {"status": "ok"}


app.include_router(routes_auth.router)
app.include_router(routes_ingest.router)
app.include_router(routes_kpi.router)
app.include_router(routes_insights.router)
app.include_router(routes_sources.router)
app.include_router(routes_analytics.router)
app.include_router(routes_assistant.router)

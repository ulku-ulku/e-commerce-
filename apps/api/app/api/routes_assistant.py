"""Mağaza AI Asistanı uç noktası — verine bağlanır, soruları yanıtlar, aksiyon alır."""
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models import User
from app.services.agent import chat

router = APIRouter(prefix="/api/assistant", tags=["assistant"])


class Msg(BaseModel):
    role: str        # user | assistant
    content: str


class ChatIn(BaseModel):
    messages: list[Msg]


@router.post("/chat")
def assistant_chat(data: ChatIn, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    history = [{"role": m.role, "content": m.content} for m in data.messages][-12:]
    return chat(db, user.org_id, history)

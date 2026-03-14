from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..auth.deps import get_current_user
from ..crud import get_tasks
from ..database import get_db
from ..llm.chat import chat_reply
from ..models import User

router = APIRouter(prefix="/chat", tags=["chat"])


class ChatRequest(BaseModel):
    message: str


class ChatResponse(BaseModel):
    reply: str


@router.post("", response_model=ChatResponse)
def chat(request: ChatRequest, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Send a message and get AI suggestions based on current tasks."""
    try:
        tasks = get_tasks(db, user_id=current_user.id, completed=False)
        reply = chat_reply(request.message.strip(), tasks)
        return ChatResponse(reply=reply)
    except ValueError as e:
        if "GEMINI_API_KEY" in str(e) or "OPENAI_API_KEY" in str(e):
            raise HTTPException(status_code=503, detail="AI chat is not configured. Set GEMINI_API_KEY or OPENAI_API_KEY.")
        raise

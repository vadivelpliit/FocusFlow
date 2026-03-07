from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..crud import get_tasks
from ..database import get_db
from ..llm.chat import chat_reply

router = APIRouter(prefix="/chat", tags=["chat"])


class ChatRequest(BaseModel):
    message: str


class ChatResponse(BaseModel):
    reply: str


@router.post("", response_model=ChatResponse)
def chat(request: ChatRequest, db: Session = Depends(get_db)):
    """Send a message and get AI suggestions based on current tasks."""
    try:
        tasks = get_tasks(db, completed=False)
        reply = chat_reply(request.message.strip(), tasks)
        return ChatResponse(reply=reply)
    except ValueError as e:
        if "OPENAI_API_KEY" in str(e):
            raise HTTPException(status_code=503, detail="AI chat is not configured. Set OPENAI_API_KEY.")
        raise

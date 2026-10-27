from fastapi import APIRouter, Depends, Request

from app.dependencies import get_owner, get_store
from app.schemas import ChatInput, ChatResponse
from app.services.chat import reply

router = APIRouter(prefix="/api", tags=["AI 채팅"])


@router.post("/chat", response_model=ChatResponse)
def chat(payload: ChatInput, request: Request, owner=Depends(get_owner), store=Depends(get_store)):
    request.app.state.limiter.check("chat-client:" + owner, 6)
    request.app.state.limiter.check("chat-ip:" + request.client.host, 12)
    return reply(payload, owner, store, request.app.state.ai_client)

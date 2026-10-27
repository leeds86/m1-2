from fastapi import APIRouter, Depends, Response

from app.dependencies import get_owner, get_store, utc_now
from app.schemas import ConversationInput, ConversationMeta, ConversationResponse
from app.routers.data import DocId
from app.services.conversations import conversation_document, require_owner

router = APIRouter(prefix="/api/conversations", tags=["대화 기록"])


@router.post("", response_model=ConversationResponse, status_code=201)
def save_conversation(payload: ConversationInput, owner=Depends(get_owner), store=Depends(get_store)):
    messages = [dict(message.model_dump(), created_at=utc_now()) for message in payload.messages]
    document = conversation_document(payload.market, messages, owner)
    return store.create("conversations", document["id"], document)


@router.get("", response_model=list[ConversationMeta])
def list_conversations(owner=Depends(get_owner), store=Depends(get_store)):
    documents = store.list("conversations", "owner", owner)
    return sorted(documents, key=lambda document: document["updated_at"], reverse=True)


@router.get("/{doc_id}", response_model=ConversationResponse)
def get_conversation(doc_id: DocId, owner=Depends(get_owner), store=Depends(get_store)):
    return require_owner(store.get("conversations", doc_id), owner)


@router.delete("/{doc_id}", status_code=204)
def delete_conversation(doc_id: DocId, owner=Depends(get_owner), store=Depends(get_store)):
    def delete(document):
        require_owner(document, owner)
        return None

    store.mutate("conversations", doc_id, delete)
    return Response(status_code=204)

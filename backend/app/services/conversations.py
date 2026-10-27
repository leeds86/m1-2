from uuid import uuid4

from app.dependencies import utc_now
from app.errors import AppError


def require_owner(document, owner):
    if document["owner"] != owner:
        raise AppError(404, "대화를 찾을 수 없습니다.")
    return document


def conversation_document(market, messages, owner):
    now = utc_now()
    return dict(id=str(uuid4()), owner=owner, market=market, title=messages[0]["content"][:60],
                messages=messages, message_count=len(messages), created_at=now, updated_at=now)

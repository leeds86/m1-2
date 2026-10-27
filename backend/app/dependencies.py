from threading import Lock
from uuid import UUID
from typing import Annotated

from fastapi import Header, Request

from app.errors import AppError
from app.repositories import FirestoreStore, SQLiteStore

_store_lock = Lock()


def get_store(request: Request):
    if request.app.state.store is None:
        with _store_lock:
            if request.app.state.store is None:
                settings = request.app.state.settings
                try:
                    request.app.state.store = (SQLiteStore(settings.sqlite_path) if settings.storage_backend == "sqlite"
                                               else FirestoreStore(settings))
                except AppError:
                    raise
                except Exception:
                    raise AppError(503, "저장소 연결에 실패했습니다. Firebase 설정을 확인하세요.") from None
    return request.app.state.store


def get_owner(x_client_id: Annotated[UUID, Header()]):
    return str(x_client_id)


def utc_now():
    from datetime import datetime, timezone

    return datetime.now(timezone.utc).isoformat()

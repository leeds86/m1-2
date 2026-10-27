from datetime import datetime, timezone
from types import SimpleNamespace

import httpx
import pytest
import sqlite3
from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app
from app.providers import OpenAIResponder, UpbitClient
from app.repositories import SQLiteStore
from app.errors import AppError


OWNER = {"X-Client-Id": "5fd8cacc-2165-4f7e-97ba-678fbca1a823"}
OTHER = {"X-Client-Id": "71452973-a4f7-4e98-a7b3-438413d7175a"}


def candle(day="2025-01-01", **overrides):
    return dict(market="KRW-BTC", date=day, value=100, open=95, high=105,
                low=90, volume=10, memo="검증", **overrides)


@pytest.fixture
def client(tmp_path):
    app = create_app(Settings(storage_backend="sqlite", sqlite_path=str(tmp_path / "test.db")),
                     ai_client=None)
    with TestClient(app) as test_client:
        yield test_client


def test_data_crud_recalculates_summary_and_persists(client):
    response = client.post("/api/data", json=candle())
    assert response.status_code == 201
    doc_id = response.json()["id"]
    assert client.get("/api/data").json()[0]["value"] == 100
    assert client.get("/api/data/summary").json()["metrics"]["latest"] == 100
    updated = candle()
    updated.update(value=102, memo="<script>alert(1)</script>")
    assert client.put(f"/api/data/{doc_id}", json=updated).status_code == 200
    assert client.get("/api/data/summary").json()["metrics"]["latest"] == 102
    assert client.get("/api/data", params={"market": "KRW-ETH"}).json() == []
    assert client.delete(f"/api/data/{doc_id}").status_code == 204
    assert client.get("/api/data/summary").json()["count"] == 0
    assert client.delete(f"/api/data/{doc_id}").status_code == 404


@pytest.mark.parametrize("overrides", [
    {"value": 0}, {"value": 106}, {"low": 101}, {"volume": -1},
    {"date": "2099-01-01"}, {"memo": "a" * 501}, {"market": "../../secret"},
    {"high": "NaN"}, {"value": "Infinity"},
])
def test_invalid_input_is_never_saved(client, overrides):
    payload = candle()
    payload.update(overrides)
    assert client.post("/api/data", json=payload).status_code == 422
    assert client.get("/api/data").json() == []


def test_duplicate_candle_does_not_overwrite_manual_record(client):
    assert client.post("/api/data", json=candle()).status_code == 201
    assert client.post("/api/data", json=candle()).status_code == 409
    row = client.get("/api/data").json()[0]
    changed = candle()
    changed["date"] = "2025-01-02"
    assert client.put(f"/api/data/{row['id']}", json=changed).status_code == 409


def test_conversations_are_saved_loaded_deleted_and_scoped(client):
    payload = {"market": "KRW-BTC", "messages": [{"role": "user", "content": "지표 설명"},
               {"role": "assistant", "content": "데이터에 근거한 설명"}]}
    saved = client.post("/api/conversations", json=payload, headers=OWNER)
    assert saved.status_code == 201
    doc_id = saved.json()["id"]
    listing = client.get("/api/conversations", headers=OWNER).json()
    assert listing[0]["id"] == doc_id
    assert "messages" not in listing[0]
    assert client.get(f"/api/conversations/{doc_id}", headers=OWNER).json()["messages"][1]["content"] == "데이터에 근거한 설명"
    assert client.get(f"/api/conversations/{doc_id}", headers=OTHER).status_code == 404
    assert client.delete(f"/api/conversations/{doc_id}", headers=OTHER).status_code == 404
    assert client.get("/api/conversations", headers=OTHER).json() == []
    assert client.get("/api/conversations").status_code == 422
    assert client.delete(f"/api/conversations/{doc_id}", headers=OWNER).status_code == 204


def test_chat_uses_summary_and_stores_both_turns(client):
    requests = []

    class Completions:
        def create(self, **kwargs):
            requests.append(kwargs)
            return SimpleNamespace(choices=[SimpleNamespace(finish_reason="stop",
                message=SimpleNamespace(content="최근 종가는 100원이며 준비 기간이 부족합니다."))])

    client.app.state.ai_client = OpenAIResponder("test-key", "test-model",
        sdk=SimpleNamespace(chat=SimpleNamespace(completions=Completions())))
    client.post("/api/data", json=candle())
    reply = client.post("/api/chat", headers=OWNER,
                        json={"market": "KRW-BTC", "message": "종가가 얼마야?"})
    assert reply.status_code == 200
    result = reply.json()
    doc_id = result["conversation_id"]
    assert result["summary"]["count"] == 1
    assert requests[0]["messages"][0]["role"] == "system"
    assert '"latest": 100.0' in requests[0]["messages"][0]["content"]
    assert "검증" not in requests[0]["messages"][0]["content"]  # Raw memos are never prompt instructions.
    assert requests[0]["max_tokens"] <= 1200
    assert requests[0]["messages"][-1] == {"role": "user", "content": "종가가 얼마야?"}
    history = client.get(f"/api/conversations/{doc_id}", headers=OWNER).json()
    assert [m["role"] for m in history["messages"]] == ["user", "assistant"]
    assert history["messages"][1]["content"] == result["answer"]
    continued = client.post("/api/chat", headers=OWNER,
                            json={"market": "KRW-BTC", "message": "한계는?", "conversation_id": doc_id})
    assert continued.status_code == 200
    assert len(requests[1]["messages"]) == 4  # System + prior turn + new question.
    assert len(client.get(f"/api/conversations/{doc_id}", headers=OWNER).json()["messages"]) == 4
    wrong_market = client.post("/api/chat", headers=OWNER,
                              json={"market": "KRW-ETH", "message": "설명", "conversation_id": doc_id})
    assert wrong_market.status_code == 409


def test_chat_missing_key_and_upstream_errors_never_create_fake_answers(client):
    client.post("/api/data", json=candle())
    request = {"market": "KRW-BTC", "message": "설명"}
    assert client.post("/api/chat", json=request, headers=OWNER).status_code == 503

    class FailedResponder:
        def respond(self, instructions, messages):
            raise RuntimeError("secret upstream details")

    client.app.state.ai_client = FailedResponder()
    response = client.post("/api/chat", json=request, headers=OWNER)
    assert response.status_code == 502
    assert "secret" not in response.text
    assert client.get("/api/conversations", headers=OWNER).json() == []


def test_no_data_chat_guides_import_without_calling_model(client):
    response = client.post("/api/chat", headers=OWNER, json={"market": "KRW-BTC", "message": "분석"})
    assert response.status_code == 409


def test_cors_and_swagger(client):
    assert client.get("/docs").status_code == 200
    assert "/api/data/summary" in client.get("/openapi.json").json()["paths"]
    allowed = client.options("/api/data", headers={"Origin": "http://localhost:5500",
                             "Access-Control-Request-Method": "POST"})
    assert allowed.headers["access-control-allow-origin"] == "http://localhost:5500"
    forbidden = client.options("/api/data", headers={"Origin": "https://untrusted.example",
                               "Access-Control-Request-Method": "POST"})
    assert "access-control-allow-origin" not in forbidden.headers


def test_upbit_completed_candles_only_and_import_preserves_manual(client):
    now = datetime(2025, 2, 1, 12, tzinfo=timezone.utc)

    def upstream(request):
        if request.url.path.endswith("market/all"):
            return httpx.Response(200, json=[{"market": "KRW-BTC", "korean_name": "비트코인", "english_name": "Bitcoin"},
                                             {"market": "BTC-ETH", "korean_name": "이더리움", "english_name": "Ethereum"}])
        assert request.url.params["to"] == "2025-02-01T00:00:00Z"
        assert request.url.params["count"] == "200"
        base = dict(market="KRW-BTC", opening_price=95, high_price=105,
                    low_price=90, trade_price=100, candle_acc_trade_volume=10)
        return httpx.Response(200, json=[dict(base, candle_date_time_utc="2025-02-01T00:00:00"),
                                        dict(base, candle_date_time_utc="2025-01-31T00:00:00"),
                                        dict(base, candle_date_time_utc="2025-01-01T00:00:00")])

    market_client = UpbitClient(client=httpx.Client(transport=httpx.MockTransport(upstream)), clock=lambda: now)
    client.app.state.market_client = market_client
    assert len(client.get("/api/markets").json()) == 1
    client.post("/api/data", json=candle())
    result = client.post("/api/data/import", json={"market": "KRW-BTC"})
    assert result.status_code == 200
    assert result.json()["imported"] == 1
    assert result.json()["skipped"] == 1
    saved = client.get("/api/data").json()
    assert len(saved) == 2
    assert saved[1]["memo"] == "검증"
    assert saved[0]["source"] == "upbit"


def test_sqlite_data_survives_new_instance(tmp_path):
    path = str(tmp_path / "persist.db")
    one = SQLiteStore(path)
    one.create("data", "key", dict(candle(), id="key"))
    two = SQLiteStore(path)
    assert two.get("data", "key")["value"] == 100


def test_sqlite_connections_close_after_transaction(tmp_path):
    store = SQLiteStore(str(tmp_path / "closed.db"))
    with store.connection() as connection:
        connection.execute("SELECT 1")
    with pytest.raises(sqlite3.ProgrammingError):
        connection.execute("SELECT 1")


def test_chat_cannot_append_to_another_browsers_conversation(client):
    saved = client.post("/api/conversations", headers=OWNER, json={"market": "KRW-BTC", "messages": [
        {"role": "user", "content": "질문"}, {"role": "assistant", "content": "답변"}]}).json()
    result = client.post("/api/chat", headers=OTHER, json={"market": "KRW-BTC", "message": "설명", "conversation_id": saved["id"]})
    assert result.status_code == 404
    assert client.get(f"/api/conversations/{saved['id']}", headers=OWNER).json()["message_count"] == 2


def test_model_requests_are_limited_per_client(client):
    body = {"market": "KRW-BTC", "message": "설명"}
    for _ in range(6):
        assert client.post("/api/chat", headers=OWNER, json=body).status_code == 409
    assert client.post("/api/chat", headers=OWNER, json=body).status_code == 429


def test_firestore_aborted_transaction_exhaustion_is_readable(monkeypatch):
    from google.api_core.exceptions import Aborted
    from google.cloud import firestore
    from app.repositories import FirestoreStore

    def exhausted(function):
        def execute(transaction):
            try:
                raise Aborted("contention")
            except Aborted as cause:
                raise ValueError("Failed to commit transaction in 3 attempts.") from cause
        return execute

    monkeypatch.setattr(firestore, "transactional", exhausted)
    store = FirestoreStore.__new__(FirestoreStore)
    store.client = SimpleNamespace(collection=lambda name: SimpleNamespace(document=lambda key: object()),
                                    transaction=lambda **kwargs: object())
    with pytest.raises(AppError) as caught:
        store.mutate("data", "record", lambda row: None)
    assert caught.value.status == 409
    assert "contention" not in caught.value.detail

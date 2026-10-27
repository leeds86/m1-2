import json

import httpx
import pytest
from openai import OpenAI

from app.config import Settings
from app.errors import AppError
from app.main import create_app
from app.providers import OpenAIResponder


def completion(content="지표 설명 완료", finish_reason="stop"):
    return {"id": "chatcmpl-test", "object": "chat.completion", "created": 0,
            "model": "gpt-5.4-mini", "choices": [{"index": 0,
            "message": {"role": "assistant", "content": content, "refusal": None},
            "finish_reason": finish_reason}],
            "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15}}


def test_codyssey_chat_contract_sends_summary_and_reads_completion():
    def handle(request):
        assert str(request.url) == "https://copa.codyssey.kr/v1/chat/completions"
        assert request.headers["authorization"] == "Bearer test-key"
        body = json.loads(request.content)
        assert body["model"] == "gpt-5.4-mini"
        assert body["messages"] == [{"role": "system", "content": "계산된 요약"},
                                    {"role": "user", "content": "요약해줘"}]
        assert body["max_tokens"] == 1000
        assert "input" not in body and "instructions" not in body
        return httpx.Response(200, json=completion())

    with httpx.Client(transport=httpx.MockTransport(handle)) as http:
        sdk = OpenAI(api_key="test-key", base_url="https://copa.codyssey.kr/v1", http_client=http)
        responder = OpenAIResponder("test-key", "gpt-5.4-mini", sdk=sdk)
        assert responder.respond("계산된 요약", [{"role": "user", "content": "요약해줘"}]) == "지표 설명 완료"


def test_configured_gateway_is_used_by_app(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setenv("OPENAI_MODEL", "gpt-5.4-mini")
    monkeypatch.setenv("OPENAI_BASE_URL", "https://copa.codyssey.kr/v1")
    settings = Settings.from_env()
    application = create_app(settings)
    try:
        assert str(application.state.ai_client.sdk.base_url) == "https://copa.codyssey.kr/v1/"
        assert settings.openai_base_url == "https://copa.codyssey.kr/v1"
    finally:
        application.state.ai_client.sdk.close()
        application.state.market_client.client.close()


@pytest.mark.parametrize("content,finish", [("", "stop"), ("  ", "stop"),
                                             (None, "stop"), ("잘린 설명", "length")])
def test_incomplete_completions_are_not_presented_as_answers(content, finish):
    with httpx.Client(transport=httpx.MockTransport(
            lambda request: httpx.Response(200, json=completion(content, finish)))) as http:
        sdk = OpenAI(api_key="test-key", http_client=http)
        with pytest.raises(AppError) as caught:
            OpenAIResponder("test-key", "gpt-5.4-mini", sdk=sdk).respond("요약", [])
        assert caught.value.status == 502


def test_invalid_credentials_return_guidance_without_upstream_details():
    with httpx.Client(transport=httpx.MockTransport(lambda request: httpx.Response(
            401, json={"error": {"message": "sensitive upstream details", "type": "authentication_error",
                                  "code": "invalid_api_key"}}))) as http:
        sdk = OpenAI(api_key="test-key", max_retries=0, http_client=http)
        with pytest.raises(AppError) as caught:
            OpenAIResponder("test-key", "gpt-5.4-mini", sdk=sdk).respond("요약", [])
        assert caught.value.status == 503
        assert "401" in caught.value.detail
        assert "OPENAI_API_KEY" in caught.value.detail
        assert "OPENAI_BASE_URL" in caught.value.detail
        assert "sensitive" not in caught.value.detail

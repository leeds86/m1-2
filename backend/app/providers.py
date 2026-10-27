"""External HTTP/SDK boundaries. Never manufacture market data or AI output."""

from datetime import datetime, timezone
from threading import Lock
from time import monotonic

import httpx
from openai import AuthenticationError

from app.errors import AppError
from app.schemas import CandleInput


class UpbitClient:
    def __init__(self, client=None, clock=None):
        self.client = client or httpx.Client(base_url="https://api.upbit.com", timeout=15)
        self.clock = clock or (lambda: datetime.now(timezone.utc))
        self._markets = None
        self._cached_at = 0
        self._lock = Lock()

    def _get(self, path, params=None):
        try:
            response = self.client.get("https://api.upbit.com" + path, params=params)
            if response.status_code in {429, 418}:
                raise AppError(429, "업비트 조회 제한입니다. 잠시 후 다시 시도하세요.")
            if response.status_code == 404:
                raise AppError(404, "업비트에서 해당 종목을 찾을 수 없습니다.")
            response.raise_for_status()
            return response.json()
        except AppError:
            raise
        except (httpx.HTTPError, ValueError):
            raise AppError(502, "업비트 데이터를 가져오지 못했습니다. 잠시 후 다시 시도하세요.") from None

    def markets(self):
        with self._lock:
            if self._markets is not None and monotonic() - self._cached_at < 300:
                return self._markets
            rows = self._get("/v1/market/all", {"is_details": "false"})
            self._markets = sorted(
                [{key: row[key] for key in ("market", "korean_name", "english_name")}
                 for row in rows if row["market"].startswith("KRW-")], key=lambda row: row["market"])
            self._cached_at = monotonic()
            return self._markets

    def candles(self, market):
        now = self.clock().astimezone(timezone.utc)
        cutoff = now.replace(hour=0, minute=0, second=0, microsecond=0)
        rows = self._get("/v1/candles/days", {"market": market, "count": 200,
                         "to": cutoff.strftime("%Y-%m-%dT%H:%M:%SZ")})
        result = []
        try:
            for row in rows:
                day = datetime.fromisoformat(row["candle_date_time_utc"]).replace(tzinfo=timezone.utc)
                if day >= cutoff:
                    continue
                if row["market"] != market:
                    raise ValueError("Unexpected market")
                payload = CandleInput(market=market, date=day.date(), value=row["trade_price"],
                                      open=row["opening_price"], high=row["high_price"], low=row["low_price"],
                                      volume=row["candle_acc_trade_volume"], memo="업비트 완료 일봉")
                result.append(payload.model_dump(mode="json"))
        except (KeyError, TypeError, ValueError):
            raise AppError(502, "업비트 응답의 캔들 형식이 올바르지 않습니다.") from None
        return sorted(result, key=lambda row: row["date"])


class OpenAIResponder:
    def __init__(self, key, model, sdk=None, base_url=None):
        if sdk is None:
            from openai import OpenAI

            sdk = OpenAI(api_key=key, base_url=base_url, timeout=40, max_retries=0)
        self.sdk = sdk
        self.model = model

    def respond(self, instructions, messages):
        # Codyssey documents the OpenAI-compatible Chat Completions contract.
        # Keep the computed summary separate from untrusted conversation input.
        options = dict(model=self.model,
                       messages=[{"role": "system", "content": instructions}, *messages],
                       max_tokens=1000)
        try:
            response = self.sdk.chat.completions.create(**options)
        except AuthenticationError:
            raise AppError(503, "AI API 인증에 실패했습니다(401). 서버의 OPENAI_API_KEY와 OPENAI_BASE_URL이 같은 발급 플랫폼의 설정인지 확인하세요.") from None
        choice = response.choices[0] if response.choices else None
        answer = choice.message.content if choice else None
        if choice is None or choice.finish_reason != "stop" or not answer or not answer.strip():
            raise AppError(502, "AI 응답이 완성되지 않았습니다. 질문을 짧게 하여 다시 시도하세요.")
        return answer.strip()

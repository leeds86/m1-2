from datetime import date as Date, datetime, timezone
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

Market = Annotated[str, Field(pattern=r"^KRW-[A-Z0-9]{1,20}$")]
Price = Annotated[float, Field(gt=0, le=1e15, allow_inf_nan=False)]


class InputModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class CandleInput(InputModel):
    market: Market = "KRW-BTC"
    date: Date
    value: Price = Field(description="종가 (KRW)")
    open: Price
    high: Price
    low: Price
    volume: float = Field(ge=0, le=1e15, allow_inf_nan=False)
    memo: str = Field(default="", max_length=500)

    @model_validator(mode="after")
    def validate_candle(self):
        if self.date >= datetime.now(timezone.utc).date():
            raise ValueError("완료된 UTC 일봉만 저장할 수 있습니다 (오늘 이전 날짜).")
        if not self.low <= min(self.open, self.value) <= max(self.open, self.value) <= self.high:
            raise ValueError("저가 ≤ 시가/종가 ≤ 고가 관계를 확인하세요.")
        return self


class CandleResponse(CandleInput):
    id: str
    source: Literal["manual", "upbit"]
    created_at: str
    updated_at: str


class ImportInput(InputModel):
    market: Market = "KRW-BTC"


class ImportResponse(BaseModel):
    market: str
    imported: int
    skipped: int
    count: int
    message: str


class Period(BaseModel):
    start: str
    end: str


class Metrics(BaseModel):
    average: float | None
    max: float | None
    min: float | None
    latest: float | None


class Trend(BaseModel):
    direction: Literal["increase", "decrease", "stable", "insufficient_data"]
    change_pct: float | None
    method: str


class Indicators(BaseModel):
    date: str
    value: float
    bb_middle: float | None
    bb_upper: float | None
    bb_lower: float | None
    rsi: float | None
    macd: float | None
    macd_signal: float | None
    macd_histogram: float | None
    volume: float
    volume_ratio: float | None


class SummaryResponse(BaseModel):
    market: str
    count: int
    unit: str
    candle_timezone: str
    period: Period | None
    metrics: Metrics
    trend: Trend
    latest_indicators: Indicators | None
    has_date_gaps: bool
    warnings: list[str]


class MessageInput(InputModel):
    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=8000)


class MessageResponse(MessageInput):
    created_at: str


class ConversationInput(InputModel):
    market: Market = "KRW-BTC"
    messages: list[MessageInput] = Field(min_length=2, max_length=60)

    @model_validator(mode="after")
    def complete_turns(self):
        if len(self.messages) % 2 or any(message.role != ("user" if i % 2 == 0 else "assistant")
                                        for i, message in enumerate(self.messages)):
            raise ValueError("사용자·AI 메시지 쌍을 순서대로 저장하세요.")
        return self


class ConversationMeta(BaseModel):
    id: str
    market: str
    title: str
    created_at: str
    updated_at: str
    message_count: int


class ConversationResponse(ConversationMeta):
    messages: list[MessageResponse]


class ChatInput(InputModel):
    market: Market = "KRW-BTC"
    message: str = Field(min_length=1, max_length=2000)
    conversation_id: Annotated[str, Field(pattern=r"^[a-f0-9-]{36}$")] | None = None


class ChatResponse(BaseModel):
    answer: str
    conversation_id: str
    summary: SummaryResponse


class MarketResponse(BaseModel):
    market: str
    korean_name: str
    english_name: str

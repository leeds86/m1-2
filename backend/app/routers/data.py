from concurrent.futures import ThreadPoolExecutor
from typing import Annotated

from fastapi import APIRouter, Depends, Path, Request, Response

from app.dependencies import get_store, utc_now
from app.errors import AppError
from app.schemas import CandleInput, CandleResponse, ImportInput, ImportResponse, Market, MarketResponse, SummaryResponse
from app.services.summary import summarize

router = APIRouter(prefix="/api", tags=["시장·데이터"])
DocId = Annotated[str, Path(pattern=r"^[A-Za-z0-9_-]{1,80}$")]


@router.get("/markets", response_model=list[MarketResponse])
def markets(request: Request):
    return request.app.state.market_client.markets()


@router.get("/data/summary", response_model=SummaryResponse)
def summary(market: Market = "KRW-BTC", store=Depends(get_store)):
    return summarize(store.list("data", "market", market), market)


@router.get("/data", response_model=list[CandleResponse])
def list_data(market: Market = "KRW-BTC", store=Depends(get_store)):
    return sorted(store.list("data", "market", market), key=lambda row: row["date"], reverse=True)


def create_record(store, payload, source):
    now = utc_now()
    doc_id = f"{payload['market']}_{payload['date']}"
    return store.create("data", doc_id, dict(payload, id=doc_id, source=source, created_at=now, updated_at=now))


@router.post("/data", response_model=CandleResponse, status_code=201)
def create_data(payload: CandleInput, store=Depends(get_store)):
    return create_record(store, payload.model_dump(mode="json"), "manual")


@router.post("/data/import", response_model=ImportResponse)
def import_data(payload: ImportInput, request: Request, store=Depends(get_store)):
    request.app.state.limiter.check("import:" + request.client.host, 4)
    rows = request.app.state.market_client.candles(payload.market)
    existing = {row["id"] for row in store.list("data", "market", payload.market)}
    pending = [row for row in rows if f"{row['market']}_{row['date']}" not in existing]

    def save_new(row):
        try:
            create_record(store, row, "upbit")
            return 1
        except AppError as exc:
            if exc.status != 409:
                raise
            # Another request may create a candle after the initial read.
            return 0

    imported = 0
    if pending:
        # Keep network latency bounded without issuing writes for known records.
        with ThreadPoolExecutor(max_workers=8) as workers:
            imported = sum(workers.map(save_new, pending))
    skipped = len(rows) - imported
    count = len(store.list("data", "market", payload.market))
    return dict(market=payload.market, imported=imported, skipped=skipped, count=count,
                message=f"{imported}개 추가, 기존 {skipped}개 보존. 완료된 UTC 일봉 기준입니다.")


@router.put("/data/{doc_id}", response_model=CandleResponse)
def update_data(doc_id: DocId, payload: CandleInput, store=Depends(get_store)):
    def update(existing):
        body = payload.model_dump(mode="json")
        if body["market"] != existing["market"] or body["date"] != existing["date"]:
            raise AppError(409, "수정 시 종목·날짜는 변경할 수 없습니다. 새 기록을 추가하세요.")
        return dict(existing, **body, source="manual", updated_at=utc_now())

    return store.mutate("data", doc_id, update)


@router.delete("/data/{doc_id}", status_code=204)
def delete_data(doc_id: DocId, store=Depends(get_store)):
    store.mutate("data", doc_id, lambda existing: None)
    return Response(status_code=204)

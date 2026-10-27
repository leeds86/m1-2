from datetime import date
from statistics import fmean

from app.services.indicators import calculate_indicators


def summarize(records: list[dict], market: str) -> dict:
    rows = sorted((row for row in records if row["market"] == market), key=lambda r: r["date"])
    prices = [float(row["value"]) for row in rows]
    trend = {"direction": "insufficient_data", "change_pct": None,
             "method": "최근 7개와 직전 7개 종가 평균 비교; ±1% 이내 유지"}
    if len(prices) >= 14:
        change = (fmean(prices[-7:]) / fmean(prices[-14:-7]) - 1) * 100
        trend.update(direction="increase" if change > 1 else "decrease" if change < -1 else "stable",
                     change_pct=round(change, 4))
    latest = calculate_indicators(rows)[-1] if rows else None
    if latest:
        latest = {key: round(value, 8) if isinstance(value, float) else value
                  for key, value in latest.items()}
    return {
        "market": market, "count": len(rows), "unit": "KRW", "candle_timezone": "UTC (KST 09:00 시작)",
        "period": {"start": rows[0]["date"], "end": rows[-1]["date"]} if rows else None,
        "metrics": {"average": round(fmean(prices), 4) if prices else None,
                    "max": max(prices) if prices else None, "min": min(prices) if prices else None,
                    "latest": prices[-1] if prices else None},
        "trend": trend, "latest_indicators": latest,
        "has_date_gaps": any((date.fromisoformat(b["date"]) - date.fromisoformat(a["date"])).days != 1
                             for a, b in zip(rows, rows[1:])),
        "warnings": (["데이터가 100개 미만입니다. 종목 데이터를 수집하세요."] if len(rows) < 100 else []),
    }

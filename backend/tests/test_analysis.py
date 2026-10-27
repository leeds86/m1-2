from datetime import date, timedelta
from math import sqrt

import pytest

from app.services.indicators import calculate_indicators
from app.services.summary import summarize


def records(prices, market="KRW-BTC"):
    return [dict(market=market, date=str(date(2025, 1, 1) + timedelta(days=i)),
                 value=float(p), open=float(p), high=float(p) + 1,
                 low=float(p) - 0.5, volume=100.0, memo="")
            for i, p in enumerate(prices)]


def test_constant_series_has_zero_macd_and_neutral_rsi():
    rows = calculate_indicators(records([100] * 50))
    assert rows[-1]["bb_middle"] == 100
    assert rows[-1]["bb_upper"] == 100
    assert rows[-1]["bb_lower"] == 100
    assert rows[-1]["rsi"] == 50
    assert rows[-1]["macd"] == 0
    assert rows[-1]["macd_signal"] == 0
    assert rows[-1]["volume_ratio"] == 1


def test_bollinger_population_std_and_warmup():
    rows = calculate_indicators(records(range(1, 41)))
    assert rows[18]["bb_middle"] is None
    assert rows[19]["bb_middle"] == 10.5
    assert rows[19]["bb_upper"] == pytest.approx(10.5 + 2 * sqrt(33.25))
    assert rows[19]["bb_lower"] == pytest.approx(10.5 - 2 * sqrt(33.25))
    assert rows[13]["rsi"] is None
    assert rows[14]["rsi"] == 100
    assert rows[24]["macd"] is None
    assert rows[25]["macd"] == pytest.approx(7)
    assert rows[32]["macd_signal"] is None
    assert rows[33]["macd_signal"] == pytest.approx(7)


def test_wilder_rsi_uses_smoothed_losses():
    prices = [44.34, 44.09, 44.15, 43.61, 44.33, 44.83, 45.10, 45.42,
              45.84, 46.08, 45.89, 46.03, 45.61, 46.28, 46.28, 46.00]
    rows = calculate_indicators(records(prices))
    assert rows[14]["rsi"] == pytest.approx(70.4641, abs=0.0001)
    assert rows[15]["rsi"] == pytest.approx(66.2496, abs=0.0001)


def test_summary_orders_filters_and_handles_empty():
    btc = records(range(10, 24))
    data = list(reversed(btc)) + records([10000], "KRW-ETH")
    result = summarize(data, "KRW-BTC")
    assert result["count"] == 14
    assert result["period"] == {"start": "2025-01-01", "end": "2025-01-14"}
    assert result["metrics"]["average"] == 16.5
    assert result["metrics"]["min"] == 10
    assert result["metrics"]["max"] == 23
    assert result["metrics"]["latest"] == 23
    assert result["trend"]["direction"] == "increase"
    assert result["trend"]["change_pct"] == pytest.approx(53.8462, abs=0.0001)
    empty = summarize([], "KRW-BTC")
    assert empty["count"] == 0
    assert empty["period"] is None
    assert empty["latest_indicators"] is None
    assert empty["trend"]["direction"] == "insufficient_data"


def test_volume_baseline_excludes_current_candle_and_zero_baseline():
    data = records([100] * 21)
    data[-1]["volume"] = 300
    assert calculate_indicators(data)[-1]["volume_ratio"] == 3
    for row in data:
        row["volume"] = 0
    assert calculate_indicators(data)[-1]["volume_ratio"] is None


def test_latest_candle_never_uses_future_prices_and_gaps_are_disclosed():
    data = records(range(1, 51))
    before = calculate_indicators(data[:35])[-1]
    after = calculate_indicators(data)[34]
    assert before == after
    data[1]["date"] = "2024-12-30"
    assert summarize(data, "KRW-BTC")["has_date_gaps"] is True

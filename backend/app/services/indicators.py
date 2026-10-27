"""Causal indicators over ascending candles. No lookahead or missing-day fill."""

from statistics import fmean, pstdev


def ema(values: list, period: int) -> list:
    result = [None] * len(values)
    valid = [(i, value) for i, value in enumerate(values) if value is not None]
    if len(valid) < period:
        return result
    position, _ = valid[period - 1]
    previous = fmean(value for _, value in valid[:period])
    result[position] = previous
    alpha = 2 / (period + 1)
    for position, value in valid[period:]:
        previous += alpha * (value - previous)
        result[position] = previous
    return result


def calculate_indicators(records: list[dict]) -> list[dict]:
    ordered = sorted(records, key=lambda row: row["date"])
    prices = [float(row["value"]) for row in ordered]
    fast, slow = ema(prices, 12), ema(prices, 26)
    macd = [None if a is None or b is None else a - b for a, b in zip(fast, slow)]
    signal = ema(macd, 9)
    average_gain = average_loss = None
    result = []
    for i, row in enumerate(ordered):
        rsi = None
        if i == 14:
            changes = [prices[j] - prices[j - 1] for j in range(1, 15)]
            average_gain = fmean(max(change, 0) for change in changes)
            average_loss = fmean(max(-change, 0) for change in changes)
        elif i > 14:
            change = prices[i] - prices[i - 1]
            average_gain = (average_gain * 13 + max(change, 0)) / 14
            average_loss = (average_loss * 13 + max(-change, 0)) / 14
        if i >= 14:
            if average_gain == 0 and average_loss == 0:
                rsi = 50.0
            elif average_loss == 0:
                rsi = 100.0
            else:
                rsi = 100 - 100 / (1 + average_gain / average_loss)
        middle = upper = lower = None
        if i >= 19:
            window = prices[i - 19:i + 1]
            middle = fmean(window)
            spread = 2 * pstdev(window)
            upper, lower = middle + spread, middle - spread
        ratio = None
        if i >= 20:
            baseline = fmean(float(item["volume"]) for item in ordered[i - 20:i])
            if baseline:
                ratio = float(row["volume"]) / baseline
        result.append({
            "date": row["date"], "value": row["value"],
            "bb_middle": middle, "bb_upper": upper, "bb_lower": lower,
            "rsi": rsi, "macd": macd[i], "macd_signal": signal[i],
            "macd_histogram": None if signal[i] is None else macd[i] - signal[i],
            "volume": row["volume"], "volume_ratio": ratio,
        })
    return result

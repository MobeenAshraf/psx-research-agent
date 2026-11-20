"""Replay the technical rule against point-in-time daily price history."""

import argparse
import csv
from datetime import date
import json
from math import isfinite
from pathlib import Path
from statistics import median

from technical.analyzer import TechnicalAnalyzer
from technical.recommendation_engine import RecommendationEngine


def load_history(path):
    with path.open(newline="", encoding="utf-8-sig") as source:
        reader = csv.DictReader(source)
        fields = set(reader.fieldnames or [])
        required = {"date", "close", "volume"}
        if not required.issubset(fields):
            raise ValueError("History must include date, close, and volume columns")
        history = [
            {"date": date.fromisoformat(row["date"]), "close": float(row["close"]), "volume": float(row["volume"])}
            for row in reader
        ]
    history.sort(key=lambda bar: bar["date"])
    if len({bar["date"] for bar in history}) != len(history):
        raise ValueError("History must contain one row per trading session")
    if any(
        not isfinite(bar["close"]) or bar["close"] <= 0
        or not isfinite(bar["volume"]) or bar["volume"] < 0
        for bar in history
    ):
        raise ValueError("History prices must be positive and volumes nonnegative")
    return history


def replay(history, *, start, cost_bps, min_turnover):
    """Generate signals at each close and simulate fills at the following close."""
    cost = cost_bps / 10_000
    analyzer = TechnicalAnalyzer()
    engine = RecommendationEngine()
    cash, shares = 1.0, 0.0
    peak = 1.0
    drawdown = 0.0
    trades = []
    skipped_trades = 0
    buy_hold_entry = None
    end_price = None
    dates = []

    for index, bar in enumerate(history[50:], start=50):
        if bar["date"] < start:
            continue
        dates.append(bar["date"])
        end_price = bar["close"]
        signal_bar = history[index - 1]
        window = history[:index]
        indicators = analyzer.calculate_indicators(window)
        signal, _, _ = engine.generate_recommendation(indicators, {}, [])

        turnover = median(row["close"] * row["volume"] for row in window[-20:])
        can_trade = (
            turnover >= min_turnover and signal_bar["volume"] > 0 and bar["volume"] > 0
            and (bar["date"] - signal_bar["date"]).days <= 7
        )
        if can_trade and buy_hold_entry is None:
            buy_hold_entry = end_price
        should_trade = (signal == "Buy" and not shares) or (signal == "Sell" and shares > 0)
        if should_trade and can_trade:
            if signal == "Buy":
                shares = cash / (end_price * (1 + cost))
                cash = 0.0
            else:
                cash = shares * end_price * (1 - cost)
                shares = 0.0
            trades.append({
                "signal_date": signal_bar["date"].isoformat(),
                "execution_date": bar["date"].isoformat(),
                "side": signal,
                "execution_close": end_price,
            })
        elif should_trade:
            skipped_trades += 1

        equity = cash + shares * end_price
        peak = max(peak, equity)
        drawdown = max(drawdown, 1 - equity / peak)

    if not dates:
        raise ValueError("No evaluation sessions after the start date and 50-session warmup")
    buy_hold_return = end_price / (buy_hold_entry * (1 + cost)) - 1 if buy_hold_entry else None
    return {
        "start": dates[0].isoformat(),
        "end": dates[-1].isoformat(),
        "sessions": len(dates),
        "one_way_cost_bps": cost_bps,
        "min_median_daily_turnover_pkr": min_turnover,
        "net_return": equity - 1,
        "buy_and_hold_return": buy_hold_return,
        "max_drawdown": drawdown,
        "trades_skipped_for_liquidity": skipped_trades,
        "trades": trades,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("history", type=Path, help="CSV with date, close, and volume columns")
    parser.add_argument("--start", type=date.fromisoformat, required=True, help="First evaluation date")
    parser.add_argument("--cost-bps", type=float, required=True, help="One-way fees and slippage")
    parser.add_argument("--min-turnover", type=float, required=True, help="Minimum median daily turnover in PKR")
    args = parser.parse_args()
    if not 0 <= args.cost_bps < 10_000 or not isfinite(args.min_turnover) or args.min_turnover < 0:
        parser.error("invalid trading cost or turnover")
    try:
        report = replay(
            load_history(args.history), start=args.start,
            cost_bps=args.cost_bps, min_turnover=args.min_turnover,
        )
    except (OSError, TypeError, ValueError) as error:
        parser.error(str(error))
    print(json.dumps(report, indent=2, allow_nan=False))


if __name__ == "__main__":
    main()

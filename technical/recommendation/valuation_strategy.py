from typing import Any, Dict, List, Tuple

from technical.recommendation.recommendation_strategy import RecommendationStrategy


class ValuationStrategy(RecommendationStrategy):
    def evaluate(
        self, indicators: Dict[str, Any], metrics: Dict[str, Any]
    ) -> Tuple[str, float, str]:
        signals: List[str] = []
        buy_score = 0.0
        sell_score = 0.0

        pb = metrics.get("price_to_book")
        if pb:
            if pb < 1.0:
                buy_score += 0.2
                signals.append(f"Undervalued (P/B: {pb:.2f})")
            elif pb > 3.0:
                sell_score += 0.2
                signals.append(f"Overvalued (P/B: {pb:.2f})")
            else:
                signals.append(f"Fair value (P/B: {pb:.2f})")

        peg = metrics.get("peg")
        if peg is not None:
            if 0 < peg < 1:
                buy_score += 0.25
                signals.append(f"Strong PEG (Price/Earnings to Growth) ratio ({peg:.2f} < 1)")
            elif peg < 0:
                sell_score += 0.1
                signals.append(f"Negative PEG (Price/Earnings to Growth) ({peg:.2f})")
            elif peg > 2:
                sell_score += 0.15
                signals.append(f"High PEG (Price/Earnings to Growth) ratio ({peg:.2f} > 2)")
            else:
                signals.append(f"PEG (Price/Earnings to Growth) ratio: {peg:.2f}")

        eps_growth = metrics.get("eps_growth")
        if eps_growth is not None:
            if eps_growth > 20:
                buy_score += 0.2
                signals.append(f"Strong EPS growth ({eps_growth:.1f}%)")
            elif eps_growth > 0:
                buy_score += 0.1
                signals.append(f"Positive EPS growth ({eps_growth:.1f}%)")
            elif eps_growth < -20:
                sell_score += 0.2
                signals.append(f"Declining EPS ({eps_growth:.1f}%)")
            elif eps_growth < 0:
                sell_score += 0.1
                signals.append(f"Negative EPS growth ({eps_growth:.1f}%)")

        net_profit_margin = metrics.get("net_profit_margin")
        if net_profit_margin is not None:
            if net_profit_margin > 20:
                buy_score += 0.15
                signals.append(f"High profit margin ({net_profit_margin:.1f}%)")
            elif net_profit_margin > 10:
                buy_score += 0.05
                signals.append(f"Good profit margin ({net_profit_margin:.1f}%)")
            elif net_profit_margin < 0:
                sell_score += 0.15
                signals.append(f"Negative margin ({net_profit_margin:.1f}%)")

        if not signals:
            return "Hold", 0.4, "No valuation data available"

        combined_signal = "; ".join(signals)

        if buy_score > sell_score and buy_score >= 0.3:
            confidence = min(0.5 + buy_score, 0.85)
            return "Buy", confidence, combined_signal
        elif sell_score > buy_score and sell_score >= 0.3:
            confidence = min(0.5 + sell_score, 0.85)
            return "Sell", confidence, combined_signal

        return "Hold", 0.5, combined_signal


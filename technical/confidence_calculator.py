"""Summarize support for the selected technical direction."""


class ConfidenceCalculator:
    def calculate_confidence(self, strategy_results, indicators, final_recommendation):
        """Return a heuristic signal-strength score, not a probability."""
        if final_recommendation == "Hold" or not strategy_results:
            return 0.0
        supporting_strength = sum(
            strength for direction, strength, _ in strategy_results
            if direction == final_recommendation
        )
        expected = ("rsi", "macd", "macd_signal", "sma_20", "sma_50", "current_price")
        coverage = sum(indicators.get(key) is not None for key in expected) / len(expected)
        return min(1.0, coverage * supporting_strength / len(strategy_results))

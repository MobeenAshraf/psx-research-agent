from typing import Optional

import pandas as pd

from technical.indicators.wilder import wilder_average


class RSICalculator:
    def calculate(self, prices: pd.Series, period: int = 14) -> Optional[float]:
        if len(prices) <= period:
            return None
        changes = prices.diff().iloc[1:]
        gains = wilder_average(changes.clip(lower=0), period)
        losses = wilder_average(-changes.clip(upper=0), period)
        if losses == 0:
            return 50.0 if gains == 0 else 100.0
        return 100 - 100 / (1 + gains / losses)

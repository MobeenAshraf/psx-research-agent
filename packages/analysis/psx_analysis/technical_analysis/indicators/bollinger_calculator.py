import pandas as pd
from typing import Dict


class BollingerCalculator:
    def calculate(self, prices: pd.Series, period: int = 20, std_dev: int = 2) -> Dict:
        middle = prices.rolling(period).mean()
        std = prices.rolling(period).std()
        return {
            'upper': float((middle + (std * std_dev)).iloc[-1]) if not middle.empty else None,
            'lower': float((middle - (std * std_dev)).iloc[-1]) if not middle.empty else None,
        }


from typing import Dict, List, Optional, Tuple
import pandas as pd


class FibonacciRetracements:
    FIB_LEVELS = [0.0, 0.236, 0.382, 0.5, 0.618, 0.786, 1.0]
    
    def calculate(self, price_data: List[Dict], period: int = 60) -> Dict:
        if len(price_data) < period:
            return {}
        
        df = pd.DataFrame(price_data)
        if df.empty:
            return {}
        
        recent_data = df.tail(period)
        
        swing_high = float(recent_data['high'].max())
        swing_low = float(recent_data['low'].min())
        
        if swing_high == swing_low:
            return {}
        
        diff = swing_high - swing_low
        current_price = float(df['close'].iloc[-1])
        
        levels = {}
        for level in self.FIB_LEVELS:
            if swing_high > swing_low:
                price_level = swing_high - (diff * level)
            else:
                price_level = swing_low + (diff * level)
            levels[f'fib_{int(level * 1000)}'] = price_level
        
        nearest_level = self._find_nearest_level(current_price, levels)
        
        return {
            'swing_high': swing_high,
            'swing_low': swing_low,
            'current_price': current_price,
            'levels': levels,
            'nearest_level': nearest_level,
            'retracement_pct': self._calculate_retracement_pct(
                current_price, swing_high, swing_low
            )
        }
    
    def _find_nearest_level(self, price: float, levels: Dict) -> Optional[str]:
        if not levels:
            return None
        
        min_diff = float('inf')
        nearest = None
        
        for level_name, level_price in levels.items():
            diff = abs(price - level_price)
            if diff < min_diff:
                min_diff = diff
                nearest = level_name
        
        return nearest
    
    def _calculate_retracement_pct(self, price: float, high: float, low: float) -> Optional[float]:
        if high == low:
            return None
        
        if high > low:
            return ((high - price) / (high - low)) * 100
        else:
            return ((price - low) / (high - low)) * 100
    
    def get_support_resistance_levels(self, fib_data: Dict) -> Dict[str, float]:
        if not fib_data or 'levels' not in fib_data:
            return {}
        
        levels = fib_data['levels']
        current = fib_data.get('current_price')
        
        support = None
        resistance = None
        
        if current:
            for level_name, level_price in sorted(levels.items(), key=lambda x: x[1]):
                if level_price < current:
                    support = level_price
                elif level_price > current and resistance is None:
                    resistance = level_price
                    break
        
        return {
            'fib_support': support,
            'fib_resistance': resistance
        }


import pandas as pd
from typing import Dict, List, Optional


class CandlestickPatterns:
    def detect_patterns(self, price_data: List[Dict]) -> List[str]:
        if len(price_data) < 3:
            return []
        
        df = pd.DataFrame(price_data)
        if df.empty:
            return []
        
        patterns = []
        
        if len(df) >= 2:
            patterns.extend(self._detect_doji(df))
            patterns.extend(self._detect_hammer(df))
            patterns.extend(self._detect_engulfing(df))
            patterns.extend(self._detect_marubozu(df))
        
        return patterns
    
    def _detect_doji(self, df: pd.DataFrame) -> List[str]:
        patterns = []
        if len(df) < 1:
            return patterns
        
        last = df.iloc[-1]
        body = abs(last['close'] - last['open'])
        total_range = last['high'] - last['low']
        
        if total_range > 0 and body / total_range < 0.1:
            patterns.append('Doji (indecision)')
        
        return patterns
    
    def _detect_hammer(self, df: pd.DataFrame) -> List[str]:
        patterns = []
        if len(df) < 1:
            return patterns
        
        last = df.iloc[-1]
        body = abs(last['close'] - last['open'])
        lower_shadow = min(last['open'], last['close']) - last['low']
        upper_shadow = last['high'] - max(last['open'], last['close'])
        
        if lower_shadow > 2 * body and upper_shadow < body:
            if last['close'] > last['open']:
                patterns.append('Hammer (bullish reversal)')
            else:
                patterns.append('Hanging Man (bearish reversal)')
        
        return patterns
    
    def _detect_engulfing(self, df: pd.DataFrame) -> List[str]:
        patterns = []
        if len(df) < 2:
            return patterns
        
        prev = df.iloc[-2]
        curr = df.iloc[-1]
        
        prev_body = abs(prev['close'] - prev['open'])
        curr_body = abs(curr['close'] - curr['open'])
        
        prev_bullish = prev['close'] > prev['open']
        curr_bullish = curr['close'] > curr['open']
        
        if curr_body > prev_body * 1.5:
            if not prev_bullish and curr_bullish:
                if curr['open'] < prev['close'] and curr['close'] > prev['open']:
                    patterns.append('Bullish Engulfing')
            elif prev_bullish and not curr_bullish:
                if curr['open'] > prev['close'] and curr['close'] < prev['open']:
                    patterns.append('Bearish Engulfing')
        
        return patterns
    
    def _detect_marubozu(self, df: pd.DataFrame) -> List[str]:
        patterns = []
        if len(df) < 1:
            return patterns
        
        last = df.iloc[-1]
        body = abs(last['close'] - last['open'])
        total_range = last['high'] - last['low']
        
        # Marubozu requires: body > 90% of range AND minimum meaningful range (>0.5% of price)
        # This avoids false positives from EOD data with minimal price movement
        min_meaningful_range = last['close'] * 0.005  # 0.5% of close price
        
        if (total_range > min_meaningful_range and 
            body / total_range > 0.95 and  # Stricter threshold (95% instead of 90%)
            body > 0):  # Must have actual price movement
            upper_shadow = last['high'] - max(last['open'], last['close'])
            lower_shadow = min(last['open'], last['close']) - last['low']
            
            # True Marubozu has minimal shadows (< 5% of body)
            if upper_shadow < body * 0.05 and lower_shadow < body * 0.05:
                if last['close'] > last['open']:
                    patterns.append('Bullish Marubozu (strong buying)')
                else:
                    patterns.append('Bearish Marubozu (strong selling)')
        
        return patterns


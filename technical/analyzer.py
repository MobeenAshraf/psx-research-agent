import pandas as pd
from typing import Dict, List, Any
from technical.indicators import (
    RSICalculator, MACDCalculator, BollingerCalculator, MovingAverageCalculator,
    VolumeAnalyzer, TrendAnalyzer, CandlestickPatterns, FibonacciRetracements,
    ATRCalculator, StochasticCalculator, OBVCalculator, VWAPCalculator, IchimokuCalculator
)


class TechnicalAnalyzer:
    def __init__(self):
        self.rsi_calc = RSICalculator()
        self.macd_calc = MACDCalculator()
        self.bb_calc = BollingerCalculator()
        self.ma_calc = MovingAverageCalculator()
        self.volume_analyzer = VolumeAnalyzer()
        self.trend_analyzer = TrendAnalyzer()
        self.candlestick = CandlestickPatterns()
        self.fibonacci = FibonacciRetracements()
        self.atr_calc = ATRCalculator()
        self.stoch_calc = StochasticCalculator()
        self.obv_calc = OBVCalculator()
        self.vwap_calc = VWAPCalculator()
        self.ichimoku_calc = IchimokuCalculator()
    
    def calculate_indicators(self, price_data: List[Dict]) -> Dict[str, Any]:
        if not self._has_sufficient_data(price_data):
            return {}
        
        df = self._prepare_dataframe(price_data)
        prices = df['close']
        highs = df.get('high', pd.Series())
        lows = df.get('low', pd.Series())
        volumes = df.get('volume', pd.Series())
        
        indicators = self._calculate_basic_indicators(prices)
        indicators.update(self.trend_analyzer.analyze_trend(prices, indicators["sma_20"], indicators["sma_50"]))
        indicators.update(self._calculate_volume_indicators(prices, volumes))
        indicators.update(self._calculate_advanced_indicators(highs, lows, prices, volumes))
        if not highs.empty and not lows.empty and highs.notna().all() and lows.notna().all():
            indicators.update(self._calculate_fibonacci_levels(df.reset_index().to_dict("records")))
        indicators["has_session_high_low"] = bool(not highs.empty and not lows.empty and highs.notna().all() and lows.notna().all())
        
        return indicators
    
    def _calculate_basic_indicators(self, prices: pd.Series) -> Dict[str, Any]:
        """Calculate basic price and momentum indicators."""
        sma_20 = self.ma_calc.calculate_sma(prices, 20)
        sma_50 = self.ma_calc.calculate_sma(prices, 50)
        rsi = self.rsi_calc.calculate(prices)
        macd_data = self.macd_calc.calculate(prices)
        bb_data = self.bb_calc.calculate(prices)
        
        return {
            'current_price': float(prices.iloc[-1]) if not prices.empty else None,
            'sma_20': sma_20,
            'sma_50': sma_50,
            'rsi': rsi,
            'macd': macd_data.get('macd'),
            'macd_signal': macd_data.get('signal'),
            'macd_crossover': macd_data.get('crossover'),
            **bb_data,
        }
    
    def _calculate_volume_indicators(self, prices: pd.Series, volumes: pd.Series) -> Dict[str, Any]:
        """Calculate volume-based indicators."""
        indicators = {}
        
        if not volumes.empty and volumes.notna().all():
            indicators.update(self.volume_analyzer.calculate_volume_indicators(prices, volumes))
            obv_data = self.obv_calc.calculate(prices, volumes)
            if obv_data.get('obv') is not None:
                indicators['obv'] = obv_data['obv']
                indicators['obv_trend'] = obv_data.get('obv_trend')
        
        return indicators
    
    def _calculate_advanced_indicators(self, highs: pd.Series, lows: pd.Series, 
                                      prices: pd.Series, volumes: pd.Series) -> Dict[str, Any]:
        """Calculate advanced indicators requiring high/low data."""
        indicators = {}
        
        if not highs.empty and not lows.empty and highs.notna().all() and lows.notna().all():
            atr = self.atr_calc.calculate(highs, lows, prices)
            if atr is not None:
                indicators['atr'] = atr
            
            stoch_data = self.stoch_calc.calculate(highs, lows, prices)
            if stoch_data.get('stoch_k') is not None:
                indicators['stoch_k'] = stoch_data['stoch_k']
            if stoch_data.get('stoch_d') is not None:
                indicators['stoch_d'] = stoch_data['stoch_d']
            
            vwap = self.vwap_calc.calculate(highs, lows, prices, volumes) if volumes.notna().all() else None
            if vwap is not None:
                indicators['vwap'] = vwap
            
            ichimoku_data = self.ichimoku_calc.calculate(highs, lows, prices)
            if ichimoku_data.get('tenkan') is not None:
                indicators.update(ichimoku_data)
        
        return indicators
    
    def _calculate_fibonacci_levels(self, price_data: List[Dict]) -> Dict[str, Any]:
        """Calculate Fibonacci retracement levels."""
        indicators = {}
        fib_data = self.fibonacci.calculate(price_data, period=60)
        if fib_data:
            indicators['fibonacci'] = fib_data
            indicators.update(self.fibonacci.get_support_resistance_levels(fib_data))
        return indicators
    
    def generate_signals(self, indicators: Dict[str, Any]) -> List[str]:
        signals = []
        signals.extend(self._check_rsi_signals(indicators))
        signals.extend(self._check_macd_signals(indicators))
        signals.extend(self._check_bollinger_signals(indicators))
        signals.extend(self._check_trend_signals(indicators))
        signals.extend(self._check_volume_signals(indicators))
        signals.extend(self._check_stochastic_signals(indicators))
        return list(dict.fromkeys(signals))
    
    def get_candlestick_patterns(self, price_data: List[Dict]) -> List[str]:
        recent = sorted(price_data, key=lambda candle: candle["date"])[-3:]
        if all(all(candle.get(field) is not None for field in ("open", "high", "low")) for candle in recent):
            return self.candlestick.detect_patterns(recent)
        return []
    
    def _has_sufficient_data(self, price_data: List[Dict]) -> bool:
        return price_data and len(price_data) >= 50
    
    def _prepare_dataframe(self, price_data: List[Dict]) -> pd.DataFrame:
        df = pd.DataFrame(price_data)
        df.set_index('date', inplace=True)
        df.sort_index(inplace=True)
        return df
    
    def _check_rsi_signals(self, indicators: Dict[str, Any]) -> List[str]:
        signals = []
        rsi = indicators.get('rsi')
        if rsi is not None:
            if rsi < 30:
                signals.append('Oversold (RSI < 30)')
            elif rsi > 70:
                signals.append('Overbought (RSI > 70)')
            elif 30 <= rsi <= 40:
                signals.append('Near oversold (RSI 30-40)')
            elif 60 <= rsi <= 70:
                signals.append('Near overbought (RSI 60-70)')
        return signals
    
    def _check_macd_signals(self, indicators: Dict[str, Any]) -> List[str]:
        crossover = indicators.get("macd_crossover")
        return [f"{crossover.capitalize()} MACD crossover"] if crossover else []

    def _check_bollinger_signals(self, indicators: Dict[str, Any]) -> List[str]:
        signals = []
        price = indicators.get('current_price')
        bb_upper = indicators.get('upper')
        bb_lower = indicators.get('lower')
        
        if price and bb_upper and bb_lower:
            if price > bb_upper:
                signals.append('Price above upper Bollinger Band')
            elif price < bb_lower:
                signals.append('Price below lower Bollinger Band')
        return signals
    
    def _check_trend_signals(self, indicators: Dict[str, Any]) -> List[str]:
        signals = []
        trend = indicators.get('trend')
        if trend:
            signals.append(f'{trend} detected')
        return signals
    
    def _check_volume_signals(self, indicators: Dict[str, Any]) -> List[str]:
        signals = []
        volume_ratio = indicators.get('volume_ratio')
        if volume_ratio is not None:
            if volume_ratio > 1.5:
                signals.append('High volume (1.5x average)')
            elif volume_ratio < 0.5:
                signals.append('Low volume (0.5x average)')
        return signals
    
    def _check_stochastic_signals(self, indicators: Dict[str, Any]) -> List[str]:
        signals = []
        stoch_k = indicators.get('stoch_k')
        stoch_d = indicators.get('stoch_d')
        if stoch_k is not None and stoch_d is not None:
            if stoch_k < 20 and stoch_d < 20:
                signals.append('Stochastic oversold (< 20)')
            elif stoch_k > 80 and stoch_d > 80:
                signals.append('Stochastic overbought (> 80)')
            elif stoch_k > stoch_d:
                signals.append('Stochastic %K above %D')
            elif stoch_k < stoch_d:
                signals.append('Stochastic %K below %D')
        return signals


# Technical Analysis Explained

## 1. What the Output Means

### Example Output:
```
ENGROH: Hold (confidence: 0.50)
  RSI: 37.47
  Price: Rs 220.00
```

**Breakdown:**
- **ENGROH**: Stock symbol
- **Hold**: Recommendation (Buy/Hold/Sell)
- **confidence: 0.50**: How confident the system is (0.0-1.0, where 1.0 = 100% confident)
- **RSI: 37.47**: Relative Strength Index (momentum indicator)
  - < 30 = Oversold (potential buy signal)
  - 30-70 = Neutral
  - > 70 = Overbought (potential sell signal)
- **Price: Rs 220.00**: Current market price

**Why "Hold"?**
- RSI 37.47 is in neutral range (not oversold/overbought)
- No strong buy/sell signals detected
- Confidence 0.50 = moderate uncertainty

## 2. Display Issue Fixed

**Problem:** Currency symbol (₨) not displaying correctly in terminal
**Solution:** Changed to "Rs" for better terminal compatibility

## 3. Enhanced Technical Analysis

### Current Indicators (Now Implemented):

#### Momentum Indicators:
- **RSI (14-period)**: Measures overbought/oversold conditions
- **MACD**: Moving Average Convergence Divergence (trend momentum)

#### Trend Indicators:
- **SMA 20**: 20-day Simple Moving Average
- **SMA 50**: 50-day Simple Moving Average
- **Trend Analysis**: Uptrend/Downtrend/Bullish/Bearish/Neutral
- **Price vs MA**: Percentage above/below moving averages

#### Volatility Indicators:
- **Bollinger Bands**: Upper/lower price bands (volatility)

#### Volume Indicators:
- **Volume Ratio**: Current volume vs 20-day average
- **Volume Signals**: High volume (>1.5x) or Low volume (<0.5x)

#### Support/Resistance:
- **Support Level**: Price floor (where buying may occur)
- **Resistance Level**: Price ceiling (where selling may occur)

### Data Requirements:

**Minimum Data Needed:**
- **50+ days** of historical price data (OHLC: Open, High, Low, Close)
- **Volume data** (for volume analysis)
- **Current price** (for real-time analysis)

**Optimal Data:**
- **365 days** (1 year) for comprehensive analysis
- Daily OHLCV data (Open, High, Low, Close, Volume)
- Timestamp for each data point

### What Each Indicator Tells You:

1. **RSI**: Is the stock oversold (buy opportunity) or overbought (sell opportunity)?
2. **MACD**: Is momentum bullish or bearish?
3. **Moving Averages**: What's the price trend direction?
4. **Bollinger Bands**: Is price at extreme levels (volatility)?
5. **Volume**: Is there strong interest (high volume) or weak interest (low volume)?
6. **Trend**: Overall market direction (up/down/sideways)

### Enhanced Output Now Shows:

```
SYS: Hold (confidence: 0.50)
  Price: Rs 148.49
  RSI: 40.43 (Near Oversold)
  Trend: Bullish
  MA20: Rs 145.20, MA50: Rs 142.10
  MACD: Bullish (MACD: 2.15, Signal: 1.80)
  Volume: 1.2x average
  Signals: Near oversold (RSI 30-40), Bullish MACD crossover, Uptrend detected
```

## Next Steps for Even Better Analysis:

1. **Candlestick Patterns**: Doji, Hammer, Engulfing patterns
2. **Fibonacci Retracements**: Support/resistance levels
3. **Stochastic Oscillator**: Additional momentum indicator
4. **ADX (Average Directional Index)**: Trend strength
5. **Volume Profile**: Price levels with high trading volume
6. **Market Sentiment**: News/social media analysis

## How to Use:

Run: `uv run python3 main.py`
Select: Option 3 (Analyze Interesting Stocks)

The system will:
1. Read stocks from Google Sheet
2. Fetch 1 year of price data for each
3. Calculate all technical indicators in parallel
4. Generate comprehensive analysis with signals
5. Display formatted results




# Candlestick Patterns & Fibonacci Retracements - Implementation Requirements

## What Was Implemented

### 1. Candlestick Patterns
**File:** `src/infrastructure/analysis/indicators/candlestick_patterns.py`

**Patterns Detected:**
- **Doji**: Indecision pattern (small body, long shadows)
- **Hammer**: Bullish reversal (long lower shadow, small body)
- **Hanging Man**: Bearish reversal (similar to hammer but bearish)
- **Bullish Engulfing**: Strong buying signal
- **Bearish Engulfing**: Strong selling signal
- **Bullish Marubozu**: Strong buying pressure (no shadows)
- **Bearish Marubozu**: Strong selling pressure (no shadows)

### 2. Fibonacci Retracements
**File:** `src/infrastructure/analysis/indicators/fibonacci_retracements.py`

**Levels Calculated:**
- 0% (Swing High)
- 23.6% (Weak support/resistance)
- 38.2% (Moderate support/resistance)
- 50% (Key level)
- 61.8% (Strong support/resistance - Golden Ratio)
- 78.6% (Very strong level)
- 100% (Swing Low)

**Outputs:**
- Swing High/Low identification
- Fibonacci support/resistance levels
- Current price retracement percentage
- Nearest Fibonacci level

## Data Requirements

### Minimum Data Needed:

#### For Candlestick Patterns:
- **OHLC Data** (Open, High, Low, Close) for each day
- **Minimum:** 2-3 days of data (for basic patterns)
- **Optimal:** 10+ days (for pattern confirmation)
- **Current Status:** ✅ Available from `get_historical_prices()` (EOD data)

#### For Fibonacci Retracements:
- **High/Low prices** over a period
- **Minimum:** 60 days of data (for swing identification)
- **Optimal:** 90-120 days (for better swing high/low detection)
- **Current Status:** ✅ Available from `get_historical_prices()` (EOD data)

### Current Data Structure:

```python
# From StockPriceService.get_historical_prices()
[
    {
        'date': datetime,
        'open': float,
        'high': float,
        'low': float,
        'close': float,
        'volume': float
    },
    ...
]
```

**Note:** PSX EOD API returns same value for OHLC in some cases. For better candlestick patterns, intraday data would be ideal but EOD data works for basic patterns.

## How It Works

### Candlestick Patterns:
1. Analyzes last 1-3 candles
2. Calculates body size vs total range
3. Checks shadow lengths (upper/lower)
4. Compares current vs previous candles
5. Returns detected patterns

### Fibonacci Retracements:
1. Finds swing high/low over last 60 days
2. Calculates price difference
3. Applies Fibonacci ratios (23.6%, 38.2%, 50%, 61.8%, 78.6%)
4. Identifies support/resistance levels
5. Calculates current price retracement percentage

## Usage in Analysis

Both features are automatically included in technical analysis:

```python
# When analyzing a stock:
analysis = analyze_use_case.execute('SYS')

# Candlestick patterns appear in:
analysis.reasoning  # e.g., ["Hammer (bullish reversal)", ...]

# Fibonacci data appears in:
analysis.indicators['fibonacci']  # Full Fibonacci data
analysis.indicators['fib_support']  # Nearest support level
analysis.indicators['fib_resistance']  # Nearest resistance level
```

## Display in CLI

When running parallel analysis (Option 3), you'll see:

```
SYS: Hold (confidence: 0.50)
  Price: Rs 148.49
  RSI: 40.43 (Near Oversold)
  Trend: Bearish
  Fib Support: Rs 145.20
  Fib Resistance: Rs 152.30
  Fib Retracement: 38.2%
  Candlestick: Hammer (bullish reversal)
  Signals: Near oversold, Bearish trend detected
```

## Limitations & Future Enhancements

### Current Limitations:
1. **EOD Data Only**: PSX EOD API may have same OHLC values
2. **Basic Patterns**: Only common patterns detected
3. **Swing Detection**: Uses 60-day window (configurable)

### Future Enhancements:
1. **Intraday Data**: Use PSX intraday API for better OHLC
2. **More Patterns**: Add Shooting Star, Three White Soldiers, etc.
3. **Pattern Confirmation**: Require multiple candles for confirmation
4. **Fibonacci Extensions**: Add 127.2%, 161.8% extension levels
5. **Multiple Timeframes**: Analyze patterns on daily/weekly charts

## Testing

Run: `uv run python3 main.py` → Option 3

The system will:
1. Fetch 365 days of historical data
2. Detect candlestick patterns
3. Calculate Fibonacci levels
4. Display in analysis results


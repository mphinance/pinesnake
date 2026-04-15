# PineSnake Supported Functions

> Auto-generated reference for Pine Script functions supported by PineSnake v0.1.0

## Moving Averages

| Pine Script | Python (pandas-ta) | Notes |
|------------|-------------------|-------|
| `ta.sma(src, len)` | `ta.sma(src, length=len)` | Simple Moving Average |
| `ta.ema(src, len)` | `ta.ema(src, length=len)` | Exponential Moving Average |
| `ta.wma(src, len)` | `ta.wma(src, length=len)` | Weighted Moving Average |
| `ta.hma(src, len)` | `ta.hma(src, length=len)` | Hull Moving Average |
| `ta.vwma(src, len)` | `ta.vwma(src, volume, length=len)` | Volume Weighted Moving Average |

## Oscillators

| Pine Script | Python (pandas-ta) | Notes |
|------------|-------------------|-------|
| `ta.rsi(src, len)` | `ta.rsi(src, length=len)` | Relative Strength Index |
| `ta.macd(src, fast, slow, sig)` | `ta.macd(src, fast=fast, slow=slow, signal=sig)` | Returns DataFrame with 3 columns |
| `ta.stoch(close, high, low, len)` | `ta.stoch(high, low, close, k=len)` | Stochastic Oscillator (needs OHLC) |
| `ta.cci(len)` | `ta.cci(high, low, close, length=len)` | Commodity Channel Index (needs OHLC) |
| `ta.mfi(len)` | `ta.mfi(high, low, close, volume, length=len)` | Money Flow Index (needs OHLC) |
| `ta.adx(len)` | `ta.adx(high, low, close, length=len)` | Average Directional Index (needs OHLC) |

## Volatility

| Pine Script | Python (pandas-ta) | Notes |
|------------|-------------------|-------|
| `ta.atr(len)` | `ta.atr(high, low, close, length=len)` | Average True Range (needs OHLC) |
| `ta.bb(src, len, mult)` | `ta.bbands(src, length=len, std=mult)` | Bollinger Bands (returns DataFrame) |

## Volume

| Pine Script | Python (pandas-ta) | Notes |
|------------|-------------------|-------|
| `ta.obv(close, volume)` | `ta.obv(close, volume)` | On-Balance Volume |

## Cross Detection

| Pine Script | Python (pandas) | Notes |
|------------|----------------|-------|
| `ta.crossover(a, b)` | `(a > b) & (a.shift(1) <= b.shift(1))` | Bullish crossover |
| `ta.crossunder(a, b)` | `(a < b) & (a.shift(1) >= b.shift(1))` | Bearish crossunder |

## Rolling Aggregates

| Pine Script | Python (pandas) | Notes |
|------------|----------------|-------|
| `ta.highest(src, len)` | `src.rolling(len).max()` | Rolling maximum |
| `ta.lowest(src, len)` | `src.rolling(len).min()` | Rolling minimum |

## Transforms

| Pine Script | Python (pandas) | Notes |
|------------|----------------|-------|
| `ta.change(src)` | `src.diff()` | Period-over-period change |
| `ta.cum(src)` | `src.cumsum()` | Cumulative sum |

## Utilities

| Pine Script | Python (pandas) | Notes |
|------------|----------------|-------|
| `na(x)` | `pd.isna(x)` | Check for NaN/null |
| `nz(x, val)` | `x.fillna(val)` | Replace NaN with value |

## Strategy Functions

| Pine Script | Tradier API | Notes |
|------------|------------|-------|
| `strategy.entry(id, strategy.long)` | `POST /accounts/{id}/orders` (buy) | Long entry |
| `strategy.close(id)` | Sell all shares of position | Flatten position |
| `strategy.exit(id, stop=X, limit=Y)` | Bracket/OCO order | Protective stop/limit |
| `strategy.cancel_all()` | Cancel all open orders | Clear all pending |

## Input Functions

| Pine Script | Generated Python | Notes |
|------------|-----------------|-------|
| `input(14)` | `int(os.getenv("PARAM_NAME", "14"))` | Generic input |
| `input.int(14, "Length")` | `int(os.getenv("LENGTH", "14"))` | Integer input |
| `input.float(1.5)` | `float(os.getenv("PARAM_NAME", "1.5"))` | Float input |
| `input.bool(true)` | `os.getenv("PARAM_NAME", "true").lower() == "true"` | Boolean input |

## Built-in Variables

| Pine Script | Python | Notes |
|------------|--------|-------|
| `close` | `df['close']` | Close price |
| `open` | `df['open']` | Open price |
| `high` | `df['high']` | High price |
| `low` | `df['low']` | Low price |
| `volume` | `df['volume']` | Volume |
| `bar_index` | `df.index` | Bar index |
| `hlc3` | `(df['high'] + df['low'] + df['close']) / 3` | Typical price |
| `hl2` | `(df['high'] + df['low']) / 2` | Median price |
| `ohlc4` | `(df['open'] + df['high'] + df['low'] + df['close']) / 4` | Average price |

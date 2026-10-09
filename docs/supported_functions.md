# PineSnake Supported Functions

Python column shows the call emitted into the generated bot, using the [`ta`](https://github.com/bukosabino/ta) library (not pandas-ta). 19 `ta.*` functions plus `na`/`nz`; `ta.bb` and `ta.bbands` are aliases. Every mapping is executed against real data in `tests/test_runtime.py`.

> Reference for Pine Script functions supported by PineSnake v0.1.0

## Moving Averages

| Pine Script | Python (`ta` library) | Notes |
|------------|-------------------|-------|
| `ta.sma(src, len)` | `ta.trend.sma_indicator(src, window=len)` | Simple Moving Average |
| `ta.ema(src, len)` | `ta.trend.ema_indicator(src, window=len)` | Exponential Moving Average |
| `ta.wma(src, len)` | `ta.trend.wma_indicator(src, window=len)` | Weighted Moving Average |
| `ta.hma(src, len)` | `ta.trend.wma_indicator(src, window=len)` | Hull Moving Average: `WMA(2*WMA(n/2) - WMA(n), sqrt(n))` |
| `ta.vwma(src, len)` | `(src*volume).rolling(len).sum() / volume.rolling(len).sum()` | Volume Weighted Moving Average |

## Oscillators

| Pine Script | Python (`ta` library) | Notes |
|------------|-------------------|-------|
| `ta.rsi(src, len)` | `ta.momentum.rsi(src, window=len)` | Relative Strength Index |
| `ta.macd(src, fast, slow, sig)` | `ta.trend.macd` / `macd_signal` / `macd_diff` packed into a DataFrame (`macd`, `signal`, `hist`) | Returns DataFrame with 3 columns |
| `ta.stoch(close, high, low, len)` | `ta.momentum.stoch(high, low, close, window=len, smooth_window=1)` | Raw %K, unsmoothed, as in Pine (needs OHLC) |
| `ta.cci(len)` | `ta.trend.cci(high, low, close, window=len)` | Commodity Channel Index (needs OHLC) |
| `ta.mfi(len)` | `ta.volume.money_flow_index(high, low, close, volume, window=len)` | Money Flow Index (needs OHLC) |
| `ta.adx(len)` | `ta.trend.adx(high, low, close, window=len)` | Average Directional Index (needs OHLC) |

## Volatility

| Pine Script | Python (`ta` library) | Notes |
|------------|-------------------|-------|
| `ta.atr(len)` | `ta.volatility.average_true_range(high, low, close, window=len)` | Average True Range (needs OHLC) |
| `ta.bb(src, len, mult)` / `ta.bbands` | `ta.volatility.bollinger_mavg` / `_hband` / `_lband` packed into a DataFrame (`basis`, `upper`, `lower`) | Same order as Pine's `[middle, upper, lower]` |

## Volume

| Pine Script | Python (`ta` library) | Notes |
|------------|-------------------|-------|
| `ta.obv(close, volume)` | `ta.volume.on_balance_volume(close, volume)` | On-Balance Volume |

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

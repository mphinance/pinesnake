# 🐍 PineSnake — Build Instructions

> **Pine Script → Python Algo Trading Converter**
> Convert TradingView strategies into standalone Python trading bots targeting Tradier.
> No subscription. No middleman. Your machine, your code, your edge.

## What This Is

An open-source CLI tool that:
1. Parses TradingView Pine Script v5 strategies
2. Extracts indicators, entry/exit logic, and parameters
3. Generates a standalone, runnable Python algo trading script
4. Targets the **Tradier API** for live/paper equity trading

```bash
pinesnake convert my_strategy.pine --tradier --timeframe 5min -o my_algo.py
```

## Why This Exists

Millions of people write strategies on TradingView but can't run them as algos without:
- TradersPost ($30+/mo SaaS)
- Hiring a developer ($$$)
- Learning to code from scratch

PineSnake converts their Pine Script to clean, readable Python they can run locally. Free. Open source.

---

## Architecture

```
Pine Script (.pine)
    ↓
Parser (pynescript library → AST)
    ↓
Analyzer (AST walker → StrategySpec dataclass)
    ↓
Code Generator (Jinja2 templates + pandas-ta mappings)
    ↓
Standalone Python Trading Bot (.py)
    ↓
Tradier API (sandbox or live)
```

## Tech Stack

| Component | Library | Why |
|-----------|---------|-----|
| Pine Script Parser | `pynescript` (pip, LGPL-3.0) | Parses Pine Script v5 into AST via ANTLR grammar |
| Indicator Mapping | `pandas-ta` | Readable TA library that maps cleanly from Pine's `ta.*` functions |
| Code Generation | `jinja2` | Template engine for generating Python output |
| CLI | `click` | Clean command-line interface |
| Data/Trading | `requests` + `pandas` | Tradier REST API calls + data manipulation |
| Config | `python-dotenv` | .env file for API keys in generated scripts |
| Scheduling | `schedule` | Simple job scheduling in generated scripts |

## Project Structure

```
pinesnake/
├── README.md                          # User-facing docs
├── BUILD.md                           # THIS FILE - build instructions
├── pyproject.toml                     # Package config + dependencies
├── pinesnake/
│   ├── __init__.py                    # Version
│   ├── cli.py                         # Click CLI (convert, validate, supported)
│   ├── parser.py                      # Wraps pynescript → AST
│   ├── analyzer.py                    # AST → StrategySpec dataclass
│   ├── codegen/
│   │   ├── __init__.py
│   │   ├── generator.py              # Orchestrator: StrategySpec → Python code
│   │   ├── indicators.py             # ta.* → pandas-ta mapping table
│   │   ├── strategy.py               # strategy.* → Tradier API mapping
│   │   └── templates/
│   │       ├── tradier_algo.py.j2    # Jinja2 template for generated Tradier algo
│   │       └── config.env.j2         # .env template for generated scripts
│   └── brokers/
│       ├── __init__.py
│       └── tradier.py                 # Tradier API client (gets embedded in output)
├── examples/
│   ├── rsi_strategy.pine              # RSI overbought/oversold
│   ├── ema_crossover.pine             # 9/21 EMA cross
│   └── macd_strategy.pine             # MACD signal cross
├── tests/
│   ├── test_parser.py
│   ├── test_analyzer.py
│   └── test_codegen.py
└── docs/
    └── supported_functions.md         # What Pine Script features are supported
```

## CLI Interface

```bash
# Convert a Pine Script to a Python algo
pinesnake convert strategy.pine --tradier --timeframe 5min -o my_algo.py

# Validate (parse-only, show what was detected)
pinesnake validate strategy.pine

# List all supported Pine Script functions
pinesnake supported
```

### CLI Flags for `convert`
- `--tradier` — target Tradier API (required for now, other brokers later)
- `--timeframe` — bar interval: 1min, 5min, 15min, 1h, 4h, 1d (default: 5min)
- `--symbol` — default symbol (default: SPY, overridable in generated .env)
- `-o / --output` — output file path (default: stdout)

## Pine Script → Python Mappings

### Indicators (ta.* → pandas-ta)

| Pine Script | pandas-ta | Notes |
|------------|-----------|-------|
| `ta.sma(src, len)` | `ta.sma(src, length=len)` | |
| `ta.ema(src, len)` | `ta.ema(src, length=len)` | |
| `ta.rsi(src, len)` | `ta.rsi(src, length=len)` | |
| `ta.macd(src, fast, slow, sig)` | `ta.macd(src, fast=fast, slow=slow, signal=sig)` | Returns DataFrame with 3 cols |
| `ta.atr(len)` | `ta.atr(high, low, close, length=len)` | Needs OHLC |
| `ta.stoch(close, high, low, len)` | `ta.stoch(high, low, close, k=len)` | |
| `ta.crossover(a, b)` | `(a > b) & (a.shift(1) <= b.shift(1))` | Manual, pandas-ta cross() is awkward |
| `ta.crossunder(a, b)` | `(a < b) & (a.shift(1) >= b.shift(1))` | Manual |
| `ta.highest(src, len)` | `src.rolling(len).max()` | Native pandas |
| `ta.lowest(src, len)` | `src.rolling(len).min()` | Native pandas |
| `ta.vwma(src, len)` | `ta.vwma(src, volume, length=len)` | |
| `ta.change(src)` | `src.diff()` | Native pandas |
| `ta.cum(src)` | `src.cumsum()` | Native pandas |
| `na(x)` | `pd.isna(x)` | |
| `nz(x, val)` | `x.fillna(val)` | |

### Strategy Functions → Tradier API

| Pine Script | Tradier API Call |
|------------|-----------------|
| `strategy.entry(id, strategy.long)` | `POST /v1/accounts/{id}/orders` (buy) |
| `strategy.close(id)` | Sell all shares of position |
| `strategy.exit(id, stop=X, limit=Y)` | Bracket/OCO order |
| `strategy.cancel_all()` | Cancel all open orders |

### Built-in Variables → DataFrame Columns

| Pine Script | Python |
|------------|--------|
| `close` | `df['close']` |
| `open` | `df['open']` |
| `high` | `df['high']` |
| `low` | `df['low']` |
| `volume` | `df['volume']` |
| `bar_index` | `df.index` |

### Input Functions → Config/.env

| Pine Script | Generated Python |
|------------|-----------------|
| `input(14)` | `int(os.getenv("PARAM_NAME", "14"))` |
| `input.int(14, "Length")` | `int(os.getenv("LENGTH", "14"))` |
| `input.float(1.5)` | `float(os.getenv("PARAM_NAME", "1.5"))` |
| `input.bool(true)` | `os.getenv("PARAM_NAME", "true").lower() == "true"` |

## Generated Output Example

The generated Python file should be a **single, self-contained, well-commented script**:

```python
#!/usr/bin/env python3
"""
Auto-generated by PineSnake from: ema_crossover.pine
Strategy: "EMA Crossover"
Generated: 2026-04-14
WARNING: DRY RUN MODE - Set DRY_RUN=false in .env to trade live
"""
import os, logging, time, requests
import pandas as pd
import pandas_ta as ta
from dotenv import load_dotenv

load_dotenv()

# ═══════════════════════════════════════
# CONFIGURATION (from Pine Script inputs)
# ═══════════════════════════════════════
FAST_LENGTH = int(os.getenv("FAST_LENGTH", "9"))
SLOW_LENGTH = int(os.getenv("SLOW_LENGTH", "21"))
SYMBOL = os.getenv("SYMBOL", "SPY")
DRY_RUN = os.getenv("DRY_RUN", "true").lower() == "true"
POSITION_SIZE = float(os.getenv("POSITION_SIZE", "100"))

# ═══════════════════════════════════════
# TRADIER API CLIENT
# ═══════════════════════════════════════
TRADIER_TOKEN = os.getenv("TRADIER_API_KEY")
TRADIER_ACCOUNT = os.getenv("TRADIER_ACCOUNT_ID")
BASE_URL = "https://sandbox.tradier.com/v1" if DRY_RUN else "https://api.tradier.com/v1"
HEADERS = {"Authorization": f"Bearer {TRADIER_TOKEN}", "Accept": "application/json"}

def fetch_bars(symbol, interval="5min", count=100):
    """Fetch OHLCV bars from Tradier."""
    # ... Tradier market data API call ...

def calculate_indicators(df):
    """Calculate strategy indicators using pandas-ta."""
    df['ema_fast'] = ta.ema(df['close'], length=FAST_LENGTH)
    df['ema_slow'] = ta.ema(df['close'], length=SLOW_LENGTH)
    return df

def check_signals(df):
    """Check for entry/exit signals."""
    last = df.iloc[-1]
    prev = df.iloc[-2]
    if prev['ema_fast'] <= prev['ema_slow'] and last['ema_fast'] > last['ema_slow']:
        return "BUY"
    if prev['ema_fast'] >= prev['ema_slow'] and last['ema_fast'] < last['ema_slow']:
        return "SELL"
    return None

def place_order(symbol, side, qty):
    """Place order via Tradier (or log in dry-run mode)."""
    if DRY_RUN:
        logging.info(f"[DRY RUN] Would {side} {qty} shares of {symbol}")
        return
    # ... actual Tradier order placement ...

def main():
    while True:
        if not is_market_open():
            time.sleep(60)
            continue
        df = fetch_bars(SYMBOL)
        df = calculate_indicators(df)
        signal = check_signals(df)
        if signal:
            place_order(SYMBOL, signal.lower(), calculate_qty(POSITION_SIZE))
        time.sleep(300)  # 5min interval

if __name__ == "__main__":
    main()
```

## V1 Scope

### ✅ Included
- Pine Script v5 parsing via `pynescript`
- ~20 common `ta.*` indicator functions via `pandas-ta`
- `strategy.entry()` (LONG ONLY), `strategy.close()`, `strategy.exit()` (basic stop/limit)
- `input()` family → .env config
- Tradier broker (equities, $0 commission)
- `--tradier` and `--timeframe` CLI flags
- DRY_RUN=true by default
- Single-symbol strategies
- Standalone generated Python files

### ❌ V2+ Future Features
- **Short selling** (`strategy.short`) — needs margin education for muggles
- **Tradovate broker** (futures: ES, NQ, CL) — different API architecture (OAuth, WebSocket, $25/mo add-on)
- **Multi-timeframe** (`security()` / `request.security()`)
- **Options strategies**
- **Custom Pine Script functions/libraries**
- **Other brokers** (Alpaca, IBKR, etc.)
- **Webhook/alert mode** (trigger on TradingView alert instead of poll)

## Build Order

1. Project scaffold + pyproject.toml + deps
2. Parser wrapper (pynescript → AST)
3. Analyzer (AST → StrategySpec dataclass)
4. Indicator mappings (ta.* → pandas-ta)
5. Code generator + Tradier Jinja2 template
6. CLI wiring (click)
7. Examples + README + tests

## Key Dependencies

```
pynescript>=0.3.0    # Pine Script v5 parser (ANTLR-based)
pandas>=2.0          # DataFrames
pandas-ta>=0.3.14    # Technical indicators
requests>=2.28       # HTTP client for Tradier
click>=8.0           # CLI framework
jinja2>=3.1          # Template engine
python-dotenv>=1.0   # .env file support
schedule>=1.2        # Job scheduling in generated code
```

## Tradier API Reference

- **Sandbox**: `https://sandbox.tradier.com/v1`
- **Production**: `https://api.tradier.com/v1`
- **Auth**: Bearer token in header
- **Market Data**: `GET /markets/history?symbol=X&interval=5min`
- **Place Order**: `POST /accounts/{id}/orders` with `class=equity&symbol=X&side=buy&quantity=N&type=market`
- **Positions**: `GET /accounts/{id}/positions`
- **Balance**: `GET /accounts/{id}/balances`
- **Market Clock**: `GET /markets/clock`

Michael has Tradier API keys in VaultGuard (Firebase Firestore, collection: "secrets", key: "TRADIER_API_KEY").

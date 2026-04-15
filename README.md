# 🐍 PineSnake

> **Pine Script → Python Algo Trading Converter**
> Convert TradingView strategies into standalone Python trading bots.
> No subscription. No middleman. Your machine, your code, your edge.

## What It Does

PineSnake is a CLI tool that:
1. **Parses** TradingView Pine Script v5 strategies
2. **Extracts** indicators, entry/exit logic, and parameters
3. **Generates** a standalone, runnable Python algo trading script
4. **Targets** broker APIs for live/paper trading

### Supported Brokers

| Broker | Status | Notes |
|--------|--------|-------|
| [Tradier](https://tradier.com) | ✅ Live | Equities, options. Free sandbox at [developer.tradier.com](https://developer.tradier.com) |
| [Tradovate](https://tradovate.com) | 🔜 Next | Futures (ES, NQ, CL, etc.). Coming in v0.2 |

## Quick Start

```bash
# Install
pip install -e .

# Convert a Pine Script to a Python trading bot
pinesnake convert examples/ema_crossover.pine --tradier --timeframe 5min -o my_algo.py

# Edit the generated .env with your broker credentials
nano my_algo.env

# Run (DRY_RUN=true by default — no real trades)
python my_algo.py
```

## Commands

```bash
# Convert a strategy
pinesnake convert strategy.pine --tradier --timeframe 5min -o output.py

# Validate/inspect a Pine Script (no code generation)
pinesnake validate strategy.pine

# List all supported Pine Script functions
pinesnake supported
```

### Convert Options

| Flag | Description | Default |
|------|-------------|---------|
| `--tradier` | Target Tradier API (required) | — |
| `--timeframe` | Bar interval: 1min, 5min, 15min, 1h, 4h, 1d | 5min |
| `--symbol` | Default trading symbol | SPY |
| `-o / --output` | Output file path | stdout |
| `--env / --no-env` | Generate companion .env file | --env |

## Safety Features

- **DRY_RUN=true by default** — Generated scripts simulate trades until you explicitly enable live mode
- **Market hours awareness** — Only runs during market open
- **Position tracking** — Checks existing positions before placing orders
- **Comprehensive logging** — Every action logged to file and console
- **Clean .env separation** — API keys and parameters in .env, never in code
- **Auto .gitignore** — Credential files automatically excluded from version control

## Supported Pine Script Functions

PineSnake supports 23 common Pine Script functions:

- **Moving Averages**: SMA, EMA, WMA, HMA, VWMA
- **Oscillators**: RSI, MACD, Stochastic, CCI, MFI, ADX
- **Volatility**: ATR, Bollinger Bands
- **Volume**: OBV
- **Cross Detection**: crossover, crossunder
- **Rolling**: highest, lowest
- **Transforms**: change, cum

See [docs/supported_functions.md](docs/supported_functions.md) for the complete mapping table.

## Architecture

```
Pine Script (.pine)
    ↓
Parser (pynescript → AST)
    ↓
Analyzer (AST → StrategySpec dataclass)
    ↓
Code Generator (Jinja2 template + pandas-ta mappings)
    ↓
Standalone Python Trading Bot (.py)
    ↓
Broker API (Tradier now, Tradovate next)
```

## Roadmap

- [x] **v0.1** — Tradier broker (equities)
- [ ] **v0.2** — Tradovate broker (futures: ES, NQ, CL, GC)
- [ ] **v0.3** — Backtesting mode via `pinesnake backtest`
- [ ] **v0.4** — Pine Script `var`/`varip` state persistence

## Requirements

- Python 3.10+
- Broker account (Tradier sandbox is free at [developer.tradier.com](https://developer.tradier.com))

## License

MIT

# PineSnake — Agent Context

PineSnake converts TradingView Pine Script v5 strategies into standalone Python trading bots. It targets broker APIs (currently Tradier, Tradovate next).

## Architecture

The system follows a classic compiler pipeline:

```
.pine source → Parser (pynescript) → Analyzer → StrategySpec → CodeGenerator (Jinja2) → .py bot
```

### Key Modules

| Module | Purpose |
|--------|---------|
| `pinesnake/parser.py` | Wraps `pynescript` library to parse Pine Script v5 into an AST |
| `pinesnake/analyzer.py` | Walks pynescript AST nodes (`Expr`, `Assign`, `If`, `Call`, `Arg`) to extract a `StrategySpec` dataclass |
| `pinesnake/codegen/generator.py` | Orchestrates StrategySpec → Python via Jinja2. Builds a symbol table mapping Pine variables to Python equivalents |
| `pinesnake/codegen/indicators.py` | Maps 19 Pine Script `ta.*` functions (plus `na`/`nz`) to `ta` library equivalents. Each `IndicatorMapping` declares output type and unpack columns |
| `pinesnake/codegen/strategy.py` | Maps `strategy.*` calls to Tradier API operations |
| `pinesnake/codegen/templates/tradier_algo.py.j2` | Jinja2 template for standalone Tradier algo bots |
| `pinesnake/brokers/tradier.py` | Reference Tradier REST API client |
| `pinesnake/cli.py` | Click CLI: `convert`, `validate`, `supported` |

### Critical Patterns

**pynescript AST quirk**: `if` blocks appear as `Expr(value=If(...))`, not top-level `If` statements. The analyzer handles this in `_handle_expr()`.

**Symbol table**: The code generator builds a mapping from Pine variable names to Python:
- Input vars → ENV key constants (e.g., `fastLength` → `FAST_EMA_LENGTH`)
- Indicator results → df column references (e.g., `rsiValue` → `last['rsi_value']`)
- Built-ins → OHLCV columns (e.g., `close` → `df['close']`)

**Condition translation**: `ta.crossover(a, b)` becomes `prev['a'] <= prev['b'] and last['a'] > last['b']` using regex with variable resolution through the symbol table.

**Multi-output indicators**: MACD, BBands, and Stochastics declare `output_type="multi_column"` and `unpack_columns=[...]` in their `IndicatorMapping`, enabling generic DataFrame unpacking.

## Commands

```bash
pinesnake convert strategy.pine --tradier --timeframe 5min -o output.py
pinesnake validate strategy.pine
pinesnake supported
```

## Testing

```bash
pip install -e ".[dev]"
pytest tests/ -v          # 71 tests: parser, analyzer, codegen, plus runtime/e2e tests that execute the generated bots
```

## Adding a New Indicator

1. Add a function in `pinesnake/codegen/indicators.py` following the `_sma` pattern
2. Add an entry to `INDICATOR_MAP` with an `IndicatorMapping`
3. For multi-column outputs, set `output_type="multi_column"` and `unpack_columns=[...]`

## Adding a New Broker

1. Create `pinesnake/brokers/newbroker.py` with the API client
2. Create `pinesnake/codegen/templates/newbroker_algo.py.j2` template
3. Add the broker flag to `pinesnake/cli.py`
4. Update `CodeGenerator` to select the correct template

## Safety

Generated scripts default to `DRY_RUN=true`. API credentials go in `.env` files which are auto-added to `.gitignore`.

## Gotchas

- String-match tests lie. `ta.trend.macd()` once shipped with a kwarg the library rejects and every MACD bot crashed on startup while all tests passed. Add new indicators to `ARGS` in `tests/test_runtime.py`; it fails if a mapping has no executed case.
- Multi-output indicators must return a `pd.DataFrame` whose columns match `unpack_columns`, in Pine's order.
- Strategy names reach the generated file's docstrings, log filename and f-strings. Go through `_display_name` / `_slug` in `generator.py`, never raw `spec.name`.
- The generated bot imports `ta` and `pandas`, so both are core dependencies, not optional.

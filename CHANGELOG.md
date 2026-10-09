# Changelog

## Unreleased

### Fixed
- **MACD bots crashed on startup.** `ta.trend.macd()` has no `window_sign` argument and returns a Series, but the generator indexed it like a DataFrame. MACD now emits a proper `macd`/`signal`/`hist` DataFrame.
- **Tuple-unpacked indicators only registered their first variable**, so `[macdLine, signalLine, histLine] = ta.macd(...)` left `signalLine` undefined (`NameError` at signal time).
- **`ta.bb` / `ta.bbands` returned only the upper band.** Now returns `[basis, upper, lower]` in Pine order.
- **`ta.vwma` was VWAP.** Now a true volume weighted moving average.
- **`ta.hma` was a plain WMA.** Now a real Hull MA.
- **`ta.stoch` was smoothed.** Pine's `ta.stoch` is raw %K; smoothing is now off.
- **Strategy names with `/`, quotes or braces broke the generated bot** (log filename, docstring, f-string). Names are now sanitized.
- `ta` added to declared dependencies; generated bots need it.

### Added
- `tests/test_runtime.py` and `tests/test_e2e.py`: execute every indicator mapping and every example bot instead of only matching strings.
- `examples/bollinger_strategy.pine`.
- README: How It Works, Limitations, Troubleshooting, Risk Warning. Corrected nonexistent `analyze` command and `--env-output` flag (real: `validate`, `--env/--no-env`).
- Function reference now shows the real `ta` library calls (it listed pandas-ta).

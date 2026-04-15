# PineSnake Architectural Review

**Status:** Draft / Initial Review  
**Date:** 2026-04-14  
**Project Scope:** Pine Script v5 to Python (Tradier API) Transpiler

---

## 1. Issue Summary

| Severity | Category | Description |
| :--- | :--- | :--- |
| **CRITICAL** | **Reliability** | **Brittle Condition Translation**: `_translate_condition` uses regex to replace `ta.crossover`. This will fail on nested expressions or complex boolean logic. |
| **HIGH** | **Correctness** | **Lack of Series Indexing Support**: Pine Script `close[n]` syntax is not properly mapped. Generated code uses `last` and `prev` only, breaking scripts that look back further. |
| **HIGH** | **Robustness** | **Multi-Output Indicator Fragility**: Handling of `ta.macd` is hardcoded in `generator.py`. Other multi-output indicators (Bollinger Bands, Stochastics) will likely produce invalid Python. |
| **MEDIUM** | **Architecture** | **Logic Duplication**: Trading logic and API client code are duplicated between `pinesnake/brokers/tradier.py` and the Jinja2 template. |
| **MEDIUM** | **Correctness** | **State Persistence**: No support for the Pine Script `var` keyword. Variables are re-evaluated every iteration without cross-bar persistence. |
| **LOW** | **Usability** | **Limited Indicator Coverage**: Only a subset of `ta.*` functions are mapped. Unsupported functions result in `None` in generated code. |

---

## 2. Specific File & Function References

### Brittle Translation Logic
- **File:** `pinesnake/codegen/generator.py`
- **Function:** `_translate_condition`
- **Issue:** Uses `re.sub` for `ta.crossover` and `ta.crossunder`. If a user writes `if (ta.crossover(a, b) and c > d)`, the regex might survive, but more complex nesting will break. A recursive AST-to-Python walker is needed here instead of regex.

### Hardcoded Indicator Handling
- **File:** `pinesnake/codegen/generator.py`
- **Function:** `_resolve_indicators` (Lines 118-132)
- **Issue:** Explicit `if ind.pine_func == "ta.macd":` block. This logic should be moved into the `IndicatorMapping` in `indicators.py` to allow the mapping to define how its results are unpacked into the DataFrame.

### Row Access Limitations
- **File:** `pinesnake/codegen/generator.py`
- **Function:** `_resolve_var`
- **Issue:** Only supports `last` and `prev`. If the Pine Script AST contains a `Subscript` node (e.g., `src[5]`), `_node_to_string` will produce `src[5]`, which `_resolve_var` will likely fail to transform into a valid pandas `iloc` or `shift` call.

### Logic Duplication
- **File:** `pinesnake/codegen/templates/tradier_algo.py.j2` vs `pinesnake/brokers/tradier.py`
- **Issue:** The template contains a full implementation of `fetch_bars`, `place_order`, etc. Changes to the "official" `tradier.py` broker will not reflect in generated bots. The template should ideally import from a helper library or the code should be injected from the broker class.

---

## 3. Architecture Quality Assessment

- **Modularization:** The separation between `Parser` -> `Analyzer` -> `Generator` is excellent. It follows a classic compiler pipeline.
- **Intermediate Representation:** `StrategySpec` is a clean dataclass that captures the essence of a strategy. It provides a good "seam" for adding new target brokers (e.g., Alpaca, IBKR) without changing the parser.
- **Templating:** Using Jinja2 for code generation is appropriate for this scale.
- **Data Handling:** Leveraging `pandas` and `pandas-ta` for the heavy lifting of technical analysis is a very strong architectural choice.

---

## 4. Testing Gaps

- **Transpilation Validation:** There are no "gold master" tests that verify the generated Python code matches expected output for complex Pine Script samples.
- **Expression Parser Tests:** `_translate_condition` and `_node_to_string` need exhaustive unit tests with edge-case Pine expressions (nested calls, ternary operators, complex boolean algebra).
- **Live Trading Simulation:** No "Paper Trading" verification suite for the generated `tradier_algo.py`.

---

## 5. Security Concerns

- **Credential Exposure:** Generated `.env` files and scripts rely on environment variables. This is standard, but the generated `config.env.j2` should include a `.gitignore` warning or the tool should automatically add `.env` to `.gitignore`.
- **Order Execution Risk:** The generated bot uses a simple `while True` loop with `time.sleep()`. It lacks sophisticated error recovery for network partitions or API rate limiting, which could lead to "zombie" positions or missed exits.

---

## 6. Extensibility Recommendations

1.  **AST-to-AST Transformation:** Instead of `_node_to_string` followed by regex, implement a `PythonNodeVisitor` that traverses the `pynescript` AST and emits idiomatic Python nodes or strings.
2.  **Broker Abstraction:** Refactor the generator to use "Provider" classes. Instead of the template having hardcoded Tradier logic, `TradierBroker.get_template_context()` should provide the necessary Python snippets.
3.  **Variable State Support:** Implement a mechanism to handle Pine Script `var` and `varip`. This would require the generated Python script to maintain a local state file or database if it's restarted.
4.  **Expansion of `indicators.py`:** Add support for more complex indicators and allow `IndicatorMapping` to define "Unpacking Logic" for multi-column returns.
5.  **Backtesting Integration:** Since the system already produces `pandas` DataFrames, adding a `backtest` command that runs the logic against historical data (using the same `check_signals` logic) would be a massive value-add.

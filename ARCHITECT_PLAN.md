# PineSnake — Agreed Action Plan

### **Final Action Plan**

1.  **CRITICAL / Bug: Fix Historical Data Access in Conditions**
    *   **Issue:** The `last`/`prev` abstraction is incorrect and prevents historical data access (e.g., `close[10]`). This leads to runtime errors or incorrect logic.
    *   **Fix:**
        1.  Remove the `last` and `prev` variables from the `check_signals` function in `pinesnake/codegen/templates/tradier_algo.py.j2`.
        2.  Update `pinesnake/codegen/generator.py` (`_translate_condition`, `_resolve_var`) to translate Pine Script array access `variable[n]` into Python `df['column'].iloc[-(n+1)]` and a plain `variable` into `df['column'].iloc[-1]`.

2.  **CRITICAL / Robustness: Implement API Retry Logic in Generated Bots**
    *   **Issue:** Generated bots lack network resiliency and will crash on transient API errors.
    *   **Fix:** Embed the `TradierClient` class and its `with_retry` decorator from `pinesnake/brokers/tradier.py` directly into the `pinesnake/codegen/templates/tradier_algo.py.j2` template. Refactor the template's main logic to instantiate and use this client for all API calls.

3.  **HIGH / Bug: Correct `4h` Timeframe Mapping**
    *   **Issue:** The `4h` timeframe is incorrectly mapped to `daily` instead of `240min` in the generated bot, causing it to trade on incorrect data.
    *   **Fix:** In `pinesnake/codegen/templates/tradier_algo.py.j2`, change the `INTERVAL_MAP` entry from `"4h": "daily"` to `"4h": "240min"`.

4.  **HIGH / Bug: Fix Multi-Output Indicator Unpacking**
    *   **Issue:** The generator produces code that causes an `IndexError` if a user unpacks fewer variables than a multi-output indicator (like `ta.macd`) provides.
    *   **Fix:**
        1.  In `pinesnake/analyzer.py`, modify `IndicatorCall` to support a list of result variables: `result_var: str | list[str]`.
        2.  Update `_handle_assign` to correctly parse tuple unpacking into this list.
        3.  Update `_resolve_indicators` in `pinesnake/codegen/generator.py` to generate unpacking code that respects the exact number of variables specified by the user.

5.  **HIGH / Bug: Fix `crossover`/`crossunder` Assignment Logic**
    *   **Issue:** Assigning `ta.crossover` or `ta.crossunder` to a variable is incorrectly handled as an indicator, leading to faulty code generation.
    *   **Fix:**
        1.  Remove `ta.crossover` and `ta.crossunder` from `INDICATOR_MAP` in `pinesnake/codegen/indicators.py`.
        2.  Enhance the `CodeGenerator` to correctly handle assignments where the expression is a cross function, ensuring it's translated as a boolean condition wherever that variable is used.
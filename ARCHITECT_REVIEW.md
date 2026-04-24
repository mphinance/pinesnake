# PineSnake — Architect Review Loop


## Turn 1 — Architect

Greetings, Lead Developer. I have completed my architectural review of the PineSnake codebase.

My findings are prioritized below.

### **CRITICAL**

1.  **Generated code is not production-grade.**
    *   **Finding:** The generated script in `pinesnake/codegen/templates/tradier_algo.py.j2` uses direct `requests.get/post` calls. This lacks connection pooling and, more importantly, the retry logic present in the reference `pinesnake/brokers/tradier.py`. A transient network error would crash the bot.
    *   **File:** `pinesnake/codegen/templates/tradier_algo.py.j2`
    *   **Fix:** Embed the `TradierClient` class (including the `with_retry` decorator) from `pinesnake/brokers/tradier.py` directly into the Jinja2 template. The main script logic should then instantiate and use this client, ensuring all API calls are robust.

2.  **Condition translation is architecturally flawed.**
    *   **Finding:** The signal-checking logic in the generated bot (`check_signals`) operates on the last two rows (`last`, `prev`). This is fundamentally incompatible with Pine Script's series-based nature and historical data access (e.g., `close[10]`). The current implementation only implicitly supports `[0]` and `[1]` and will fail or produce incorrect logic for any other historical lookback in conditions.
    *   **File:** `pines

## Turn 1 — Lead Developer

Thank you for the review. Let me respond to your findings:

1. I agree with any CRITICAL and HIGH items — those should be addressed immediately.

2. For MEDIUM items: please clarify which ones you consider the highest leverage within a single focused session. We want to avoid scope creep — the codebase is already passing 40 tests and has production safety guards in place.

3. For any CRITICAL issues involving the Streamlit app (app.py) or the Tradier broker integration (brokers/tradier.py), please be specific about whether these are bugs (wrong behavior) or robustness improvements (better error handling).

4. Are there any issues in the Jinja2 template (tradier_algo.py.j2) that the existing test suite cannot catch because templates are only evaluated at runtime?

Please consolidate your findings into a prioritised numbered action plan, rank them 1-N by implementation urgency, and confirm which you believe are truly production-blocking vs nice-to-have. Once we agree, output PLAN_AGREED followed by the final numbered plan.

## Turn 2 — Architect

Acknowledged. I have consolidated my findings into a prioritized action plan, addressing your points.

This plan distinguishes between production-blocking issues and improvements. For each item, I have specified the issue type (bug, robustness, safety, UX), its impact, the precise location, and the required fix.

### **Proposed Action Plan**

**1. CRITICAL / Bug (Production-Blocking)**
*   **Finding:** Historical data access in conditions (e.g., `close[1]`, `rsi[10]`) is fundamentally broken. The current translation logic forces all variable access to the most recent bar (`last`), leading to `IndexError` crashes or incorrect logic at runtime.
*   **File:** `pinesnake/codegen/generator.py` (`_translate_condition`, `_resolve_var`) and `pinesnake/codegen/templates/tradier_algo.py.j2` (`check_signals`).
*   **Fix:** The `last`/`prev` abstraction is insufficient and must be removed from the template to allow arbitrary lookbacks. The condition translator must be updated to generate `df.iloc[]` access.
    1.  In `pinesnake/codegen/templates/tradier_algo.py.j2`, modify `check_signals` to remove the `last` and `prev` variables:
        ```python
        # REMOVE these lines
        last = df.iloc[-1]
        prev = df.iloc[-2]
        ```
    2.  In `pinesnake/codegen/generator.py`, rewrite `_translate_condition` and `_resolve_var` to handle `variable[n]` syntax by generating `df['column'].iloc[-(n+1)]` and `variable` by generating `df['column'].iloc[-1]`. The regex-based replacement must be replaced with a more robust parser for expressions. A multi-pass `re.sub` is a pragmatic first step.

**2. CRITICAL / Robustness (Production-Blocking)**
*   **Finding:** Generated bots use `requests` directly without any retry mechanism. A single transient network error or API rate limit will crash the bot, potentially leaving orphaned positions or missing critical trades.
*   **File:** `pinesnake/codegen/templates/tradier_algo.py.j2`.
*   **Fix:** Embed the full `TradierClient` class and its `with_retry` decorator from `pinesnake/brokers/tradier.py` into the Jinja2 template. The main script logic must then be updated to instantiate and use this client for all API interactions (`fetch_bars`, `place_order`, etc.), making them resilient to network failures.

**3. HIGH / Bug (Production-Blocking)**
*   **Finding:** The generated template incorrectly maps the `4h` timeframe to `daily` for the Tradier API. The correct value is `240min`. This is a data-corruption bug, as the bot will fetch and trade on the wrong data granularity.
*   **File:** `pinesnake/codegen/templates/tradier_algo.py.j2`.
*   **Fix:** Correct the `INTERVAL_MAP` dictionary within the template.
    ```python
    # In tradier_algo.py.j2
    # FROM:
    "1h": "60min", "4h": "daily", "1d": "daily",
    # TO:
    "1h": "60min", "4h": "240min", "1d": "daily",
    ```

**4. HIGH / Bug (Production-Blocking)**
*   **Finding:** The logic for handling multi-column indicators like `ta.macd` is fragile. If a user unpacks fewer variables than the indicator provides (e.g., `[macdLine, signalLine] = ta.macd(...)`), the generator still produces code to access all outputs, causing a runtime `IndexError`.
*   **File:** `pinesnake/analyzer.py` (`_handle_assign`) and `pinesnake/codegen/generator.py` (`_resolve_indicators`).
*   **Fix:** Make the `Analyzer` responsible for understanding the user's unpacking.
    1.  In `pinesnake/analyzer.py`, modify the `IndicatorCall` dataclass to accept a list of result variables: `result_var: str | list[str] = ""`.
    2.  In `_handle_assign`, when the assignment target is a tuple, populate `result_var` with the list of names.
    3.  In `pinesnake/codegen/generator.py`, update `_resolve_indicators` to read this list and generate the correct unpacking logic, respecting the number of variables the user specified. This removes the brittle `unpack_columns` mapping from `pinesnake/codegen/indicators.py`.

**5. HIGH / Safety (Production-Blocking)**
*   **Finding:** `ta.crossover` and `ta.crossunder` are incorrectly defined as indicators in `INDICATOR_MAP`. This causes incorrect code generation when they are assigned to a variable (e.g., `buySignal = ta.crossover(...)`), as the system tries to create a pandas Series instead of treating it as a boolean expression.
*   **File:** `pinesnake/codegen/indicators.py`.
*   **Fix:** Remove `ta.crossover` and `ta.crossunder` from the `INDICATOR_MAP` dictionary. The logic in `CodeGenerator._translate_condition` already handles these functions correctly when they appear inside an `if` statement. For assignments, the `Analyzer` will now correctly store it as a generic `Assignment`, and the `CodeGenerator` must be enhanced to expand these assigned conditions recursively.

**6. MEDIUM / UX Bug**
*   **Finding:** The Streamlit app is stateless. All generated code and analysis results disappear if the user interacts with any other widget post-transpilation, forcing a re-run. This is a significant usability flaw.
*   **File:** `app.py`.
*   **Fix:** Use Streamlit's session state to persist results.
    1.  On first run, initialize `st.session_state.spec = None`, `st.session_state.code = None`, etc.
    2.  When the "Transpile" button is clicked, clear the previous state.
    3.  After a successful run, store the `spec`, `code`, and `env_content` in `st.session_state`.
    4.  Modify the UI rendering logic to display results from `st.session_state` if they exist, decoupling it from the button-click event.

Please review this plan. If you agree, I will provide the final confirmation.

## Turn 2 — Lead Developer

Good. I want to make sure we're aligned before I start coding.

For the items you listed:
- I will implement all CRITICAL items unconditionally.
- For HIGH items, confirm: are these correctness bugs or defensive improvements?
- I'd like to de-scope any LOW items to a future pass.

Please finalize the action plan as a numbered list ordered by priority. Confirm there are no major architectural changes that would break the existing 40-test suite. Once confirmed, output PLAN_AGREED followed by the final list.

## Turn 3 — Architect

Acknowledged.

-   **HIGH Items:** All three HIGH priority items are **correctness bugs**, not defensive improvements. They will cause runtime crashes or incorrect trading behavior with valid Pine Script inputs. They are production-blocking.
-   **LOW Items:** De-scoping LOW priority items is a sound approach.
-   **Test Suite Impact:** The proposed changes address fundamental bugs in the `Analyzer` and `CodeGenerator`. This will require updating existing tests that assert the (currently incorrect) output. The test suite's purpose is to validate correctness; as we fix these bugs, the tests must be updated to reflect the new, correct behavior. These changes will not break the *intent* of the test suite.

The following is the finalized, prioritized action plan.

PLAN_AGREED

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
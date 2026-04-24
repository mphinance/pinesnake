"""
PineSnake Code Generator — Orchestrates StrategySpec → Python trading bot.

This is the core engine that takes a fully analyzed StrategySpec and
produces a standalone, runnable Python script targeting the Tradier API.
"""

from __future__ import annotations

import logging
import re
from datetime import datetime
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

from pinesnake.analyzer import (
    Direction,
    InputType,
    StrategyAction,
    StrategySpec,
)
from pinesnake.codegen.indicators import BUILTIN_VARS, INDICATOR_MAP, resolve_indicator

logger = logging.getLogger(__name__)

# Template directory
TEMPLATE_DIR = Path(__file__).parent / "templates"


class CodeGenerator:
    """
    Generates standalone Python trading scripts from a StrategySpec.

    The generator:
    1. Resolves all indicator calls to pandas-ta equivalents
    2. Builds signal detection logic from strategy calls + conditions
    3. Renders the Jinja2 template with all resolved components
    4. Optionally generates a companion .env config file
    """

    def __init__(
        self,
        timeframe: str = "5min",
        symbol: str = "SPY",
    ):
        self.timeframe = timeframe
        self.symbol = symbol

        self.jinja_env = Environment(
            loader=FileSystemLoader(str(TEMPLATE_DIR)),
            autoescape=select_autoescape([]),
            trim_blocks=True,
            lstrip_blocks=True,
            keep_trailing_newline=True,
        )

    def generate(self, spec: StrategySpec) -> str:
        """
        Generate a complete Python trading script from a StrategySpec.

        Args:
            spec: Analyzed strategy specification.

        Returns:
            Complete Python source code as string.
        """
        logger.info(f"Generating code for: {spec.name}")

        # Resolve indicators
        indicators = self._resolve_indicators(spec)

        # Build signal logic
        signals = self._build_signals(spec)

        # Build parameter list
        params = self._build_params(spec)

        # Render template
        template = self.jinja_env.get_template("tradier_algo.py.j2")
        code = template.render(
            strategy_name=spec.name,
            source_file=spec.source_file or "unknown.pine",
            generated_date=datetime.now().strftime("%Y-%m-%d %H:%M"),
            default_symbol=self.symbol,
            timeframe=self.timeframe,
            params=params,
            indicators=indicators,
            signals=signals,
        )

        logger.info(f"Generated {len(code)} chars of Python code")
        return code

    def generate_env(self, spec: StrategySpec) -> str:
        """
        Generate a .env config file for the strategy.

        Args:
            spec: Analyzed strategy specification.

        Returns:
            .env file content as string.
        """
        params = self._build_params(spec)
        template = self.jinja_env.get_template("config.env.j2")
        return template.render(
            strategy_name=spec.name,
            generated_date=datetime.now().strftime("%Y-%m-%d %H:%M"),
            default_symbol=self.symbol,
            timeframe=self.timeframe,
            params=params,
        )

    def _resolve_indicators(self, spec: StrategySpec) -> list[dict]:
        """Resolve all indicator calls to Python code."""
        indicators = []

        # Build input name → env key mapping for arg substitution
        input_map = {inp.name: inp.env_key for inp in spec.inputs}

        for ind in spec.indicators:
            # Resolve indicator args: replace input variable names with config constants
            resolved_args = []
            for arg in ind.args:
                if arg in input_map:
                    resolved_args.append(input_map[arg])
                else:
                    resolved_args.append(arg)

            resolved_kwargs = {}
            for k, v in ind.kwargs.items():
                if v in input_map:
                    resolved_kwargs[k] = input_map[v]
                else:
                    resolved_kwargs[k] = v

            python_code = resolve_indicator(ind.pine_func, resolved_args, resolved_kwargs)

            if python_code is None:
                logger.warning(f"Unsupported indicator: {ind.pine_func} — skipping")
                python_code = f"None  # UNSUPPORTED: {ind.pine_func}"

            var_name = _sanitize_var(ind.result_var)
            mapping = INDICATOR_MAP.get(ind.pine_func)

            if ind.result_vars:
                # Tuple-unpack assignment: user declared N vars, e.g. [macdLine, signalLine] = ta.macd(...)
                # Use the declared var names, capped to available unpack_columns.
                unpack_cols = (mapping.unpack_columns or []) if mapping else []
                lines = [f"_tmp_{var_name} = {python_code}"]
                for i, user_var in enumerate(ind.result_vars):
                    col_key = _sanitize_var(user_var)
                    if i < len(unpack_cols):
                        # Named column from the mapping (e.g. ta.trend.macd().iloc[:, i])
                        lines.append(f"    df['{col_key}'] = _tmp_{var_name}.iloc[:, {i}] if hasattr(_tmp_{var_name}, 'iloc') else _tmp_{var_name}")
                    else:
                        lines.append(f"    df['{col_key}'] = _tmp_{var_name}.iloc[:, {i}]")
                assignment = "\n".join(lines)
            elif mapping and mapping.output_type == "multi_column" and mapping.unpack_columns:
                # Single var on LHS but indicator is multi-column: assign all columns
                lines = [f"_tmp_{var_name} = {python_code}"]
                for i, col_suffix in enumerate(mapping.unpack_columns):
                    lines.append(f"    df['{var_name}_{col_suffix}'] = _tmp_{var_name}.iloc[:, {i}]")
                assignment = "\n".join(lines)
            else:
                assignment = f"df['{var_name}'] = {python_code}"

            indicators.append({
                "pine_func": ind.pine_func,
                "result_var": var_name,
                "python_code": python_code,
                "assignment": assignment,
            })

        return indicators

    def _build_signals(self, spec: StrategySpec) -> list[dict]:
        """Build signal detection code blocks from strategy calls."""
        signals = []

        # Build a symbol table: Pine variable name → Python expression
        symbol_table = self._build_symbol_table(spec)

        for sc in spec.strategy_calls:
            if sc.action == StrategyAction.ENTRY:
                signal_type = "BUY" if sc.direction == Direction.LONG else "SELL"
                condition = self._translate_condition(sc.condition, symbol_table)
                code = self._build_signal_block(signal_type, condition, sc.trade_id)
                signals.append({"code": code, "type": signal_type})

            elif sc.action == StrategyAction.CLOSE:
                condition = self._translate_condition(sc.condition, symbol_table)
                code = self._build_signal_block("SELL", condition, sc.trade_id)
                signals.append({"code": code, "type": "SELL"})

            elif sc.action == StrategyAction.EXIT:
                condition = self._translate_condition(sc.condition, symbol_table)
                code = self._build_signal_block("SELL", condition, sc.trade_id)
                signals.append({"code": code, "type": "EXIT"})

        return signals

    def _build_symbol_table(self, spec: StrategySpec) -> dict[str, str]:
        """
        Build a mapping from Pine Script variable names to their Python equivalents.

        Examples:
            rsiValue → df['rsi_value'] (indicator column)
            fastLength → FAST_EMA_LENGTH (input/config variable)
            overbought → OVERBOUGHT_LEVEL (input/config variable)
            close → df['close'] (built-in)
        """
        table: dict[str, str] = {}

        # Built-in variables
        table.update(BUILTIN_VARS)

        # Input parameters → their ENV key constants
        for inp in spec.inputs:
            table[inp.name] = inp.env_key

        # Indicator result variables → df column references
        for ind in spec.indicators:
            col_name = _sanitize_var(ind.result_var)
            table[ind.result_var] = f"df['{col_name}']"

        return table

    def _build_signal_block(self, signal_type: str, condition: str, trade_id: str) -> str:
        """Build a Python if-block for signal detection."""
        if not condition or condition == "unknown":
            raise ValueError(f"Unparseable condition for trade_id: '{trade_id}'. Cannot generate safe trading logic.")
            
        try:
            compile(condition, "<string>", "eval")
        except SyntaxError as e:
            raise ValueError(f"Translated condition is not valid Python syntax for trade_id '{trade_id}': {condition}") from e

        return (
            f"# Signal: {trade_id}\n"
            f"    if {condition}:\n"
            f"        return \"{signal_type}\""
        )

    def _translate_condition(self, condition: str, symbol_table: dict[str, str]) -> str:
        """
        Translate a Pine Script condition expression to Python/pandas.

        Handles:
          - ta.crossover(a, b) → prev_a <= prev_b and last_a > last_b
          - ta.crossunder(a, b) → prev_a >= prev_b and last_a < last_b
          - Variable name resolution via symbol table
          - Built-in Pine variables → df column references
        """
        if not condition:
            return ""

        result = condition

        # Handle ta.crossover(a, b) → proper prev/last comparison
        crossover_pattern = r"ta\.crossover\(([^,]+),\s*([^)]+)\)"
        def _replace_crossover(m):
            a_raw, b_raw = m.group(1).strip(), m.group(2).strip()
            a_last = self._resolve_var(a_raw, symbol_table, -1)
            a_prev = self._resolve_var(a_raw, symbol_table, -2)
            b_last = self._resolve_var(b_raw, symbol_table, -1)
            b_prev = self._resolve_var(b_raw, symbol_table, -2)
            return (
                f"not pd.isna({a_prev}) and not pd.isna({b_prev}) "
                f"and not pd.isna({a_last}) and not pd.isna({b_last}) "
                f"and {a_prev} <= {b_prev} and {a_last} > {b_last}"
            )

        result = re.sub(crossover_pattern, _replace_crossover, result)

        # Handle ta.crossunder(a, b) → proper prev/last comparison
        crossunder_pattern = r"ta\.crossunder\(([^,]+),\s*([^)]+)\)"
        def _replace_crossunder(m):
            a_raw, b_raw = m.group(1).strip(), m.group(2).strip()
            a_last = self._resolve_var(a_raw, symbol_table, -1)
            a_prev = self._resolve_var(a_raw, symbol_table, -2)
            b_last = self._resolve_var(b_raw, symbol_table, -1)
            b_prev = self._resolve_var(b_raw, symbol_table, -2)
            return (
                f"not pd.isna({a_prev}) and not pd.isna({b_prev}) "
                f"and not pd.isna({a_last}) and not pd.isna({b_last}) "
                f"and {a_prev} >= {b_prev} and {a_last} < {b_last}"
            )

        result = re.sub(crossunder_pattern, _replace_crossunder, result)

        # Replace remaining Pine variable references with df.iloc[] access
        tokens = list(set(re.findall(r'\b[a-zA-Z_][a-zA-Z0-9_]*\b', result)))
        tokens.sort(key=len, reverse=True)
        _skip = {"and", "or", "not", "True", "False", "None", "pd", "isna", "df", "iloc"}
        for token in tokens:
            if token in symbol_table and token not in _skip:
                resolved = self._resolve_var(token, symbol_table, -1)
                result = re.sub(rf"(?<!\[')\b{re.escape(token)}\b(?!'\])", resolved, result)

        return result

    def _resolve_var(self, name: str, symbol_table: dict[str, str], iloc_index: int = -1) -> str:
        """
        Resolve a Pine Script variable name to its Python df.iloc[] equivalent.

        Args:
            name: Pine Script variable name or numeric literal.
            symbol_table: Maps Pine names to their Python representations.
            iloc_index: Negative integer iloc position. -1 = latest bar, -2 = previous bar.

        Returns:
            Python expression string suitable for use in a boolean condition.
        """
        name = name.strip()

        # Numeric literal — return as-is
        try:
            float(name)
            return name
        except ValueError:
            pass

        # Symbol table lookup
        if name in symbol_table:
            py_ref = symbol_table[name]
            if py_ref.startswith("df["):
                # df['col_name'] → df['col_name'].iloc[index]
                return f"{py_ref}.iloc[{iloc_index}]"
            # Config constant (uppercase ENV key) — no row access needed
            return py_ref

        # Built-in OHLCV
        if name in BUILTIN_VARS:
            return f"df['{name}'].iloc[{iloc_index}]"

        # Unknown — return as-is
        return name

    def _build_params(self, spec: StrategySpec) -> list[dict]:
        """Build parameter list for template rendering."""
        params = []
        for inp in spec.inputs:
            cast_map = {
                InputType.INT: "int",
                InputType.FLOAT: "float",
                InputType.BOOL: 'lambda x: x.lower() == "true"',
                InputType.STRING: "str",
                InputType.SOURCE: "str",
            }
            python_cast = cast_map.get(inp.input_type, "str")

            # For bool, use special pattern
            if inp.input_type == InputType.BOOL:
                python_cast = f'os.getenv("{inp.env_key}", "{inp.default_value}").lower() == "true"  #'
                # Actually, let's use a clean pattern
                python_cast = "lambda x: x.lower() == 'true'"

            params.append({
                "name": inp.name,
                "title": inp.title,
                "env_key": inp.env_key,
                "default_value": inp.default_value,
                "python_cast": cast_map.get(inp.input_type, "str"),
                "input_type": inp.input_type.value,
            })

        return params


def _sanitize_var(name: str) -> str:
    """Sanitize a variable name for Python (lowercase, underscores)."""
    import re
    # camelCase → snake_case
    name = re.sub(r"([a-z])([A-Z])", r"\1_\2", name)
    # Remove invalid chars
    name = re.sub(r"[^a-zA-Z0-9_]", "_", name)
    return name.lower().strip("_")


def generate(
    spec: StrategySpec,
    timeframe: str = "5min",
    symbol: str = "SPY",
) -> str:
    """
    Convenience function: generate Python code from a StrategySpec.

    Args:
        spec: Analyzed strategy specification.
        timeframe: Bar interval (1min, 5min, 15min, 1h, 4h, 1d).
        symbol: Default trading symbol.

    Returns:
        Complete Python source code as string.
    """
    gen = CodeGenerator(timeframe=timeframe, symbol=symbol)
    return gen.generate(spec)


def generate_env(
    spec: StrategySpec,
    timeframe: str = "5min",
    symbol: str = "SPY",
) -> str:
    """
    Convenience function: generate .env config from a StrategySpec.

    Args:
        spec: Analyzed strategy specification.
        timeframe: Bar interval.
        symbol: Default trading symbol.

    Returns:
        .env file content as string.
    """
    gen = CodeGenerator(timeframe=timeframe, symbol=symbol)
    return gen.generate_env(spec)

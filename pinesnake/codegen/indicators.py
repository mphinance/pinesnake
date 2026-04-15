"""
PineSnake Indicator Mappings — ta.* → Python `ta` library equivalents.

This module defines how Pine Script's ta.* functions map to their
Python equivalents using the `ta` library (https://github.com/bukosabino/ta).
The code generator uses this table to produce correct ta-library code
in the output script.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable


@dataclass
class IndicatorMapping:
    """
    Mapping from a Pine Script ta.* function to its Python equivalent.

    Attributes:
        pine_name: Pine Script function name (e.g., "ta.sma")
        python_expr: A callable or template that generates the Python code.
            Receives (args: list[str], kwargs: dict[str, str]) and returns a code string.
        needs_ohlc: If True, the function needs high/low/close columns explicitly.
        notes: Documentation notes for the supported_functions listing.
        output_type: "single" (default), "multi_column" (DataFrame), or "boolean".
        unpack_columns: For multi_column outputs, list of column suffixes to unpack.
            E.g., ["macd", "signal", "hist"] for MACD.
    """
    pine_name: str
    python_expr: Callable[[list[str], dict[str, str]], str]
    needs_ohlc: bool = False
    notes: str = ""
    output_type: str = "single"
    unpack_columns: list[str] | None = None


# ═══════════════════════════════════════════════
# INDICATOR FUNCTIONS (using `ta` library API)
# ═══════════════════════════════════════════════

def _sma(args: list[str], kwargs: dict[str, str]) -> str:
    src = args[0] if args else kwargs.get("source", "df['close']")
    length = args[1] if len(args) > 1 else kwargs.get("length", "14")
    return f"ta.trend.sma_indicator({src}, window={length})"


def _ema(args: list[str], kwargs: dict[str, str]) -> str:
    src = args[0] if args else kwargs.get("source", "df['close']")
    length = args[1] if len(args) > 1 else kwargs.get("length", "14")
    return f"ta.trend.ema_indicator({src}, window={length})"


def _rsi(args: list[str], kwargs: dict[str, str]) -> str:
    src = args[0] if args else kwargs.get("source", "df['close']")
    length = args[1] if len(args) > 1 else kwargs.get("length", "14")
    return f"ta.momentum.rsi({src}, window={length})"


def _macd(args: list[str], kwargs: dict[str, str]) -> str:
    src = args[0] if args else kwargs.get("source", "df['close']")
    fast = args[1] if len(args) > 1 else kwargs.get("fast", "12")
    slow = args[2] if len(args) > 2 else kwargs.get("slow", "26")
    signal = args[3] if len(args) > 3 else kwargs.get("signal", "9")
    # Returns individual components — handled by unpack logic
    return f"ta.trend.macd({src}, window_slow={slow}, window_fast={fast}, window_sign={signal})"


def _macd_line(args: list[str], kwargs: dict[str, str]) -> str:
    src = args[0] if args else kwargs.get("source", "df['close']")
    fast = args[1] if len(args) > 1 else kwargs.get("fast", "12")
    slow = args[2] if len(args) > 2 else kwargs.get("slow", "26")
    return f"ta.trend.macd({src}, window_slow={slow}, window_fast={fast})"


def _macd_signal(args: list[str], kwargs: dict[str, str]) -> str:
    src = args[0] if args else kwargs.get("source", "df['close']")
    fast = args[1] if len(args) > 1 else kwargs.get("fast", "12")
    slow = args[2] if len(args) > 2 else kwargs.get("slow", "26")
    signal = args[3] if len(args) > 3 else kwargs.get("signal", "9")
    return f"ta.trend.macd_signal({src}, window_slow={slow}, window_fast={fast}, window_sign={signal})"


def _macd_hist(args: list[str], kwargs: dict[str, str]) -> str:
    src = args[0] if args else kwargs.get("source", "df['close']")
    fast = args[1] if len(args) > 1 else kwargs.get("fast", "12")
    slow = args[2] if len(args) > 2 else kwargs.get("slow", "26")
    signal = args[3] if len(args) > 3 else kwargs.get("signal", "9")
    return f"ta.trend.macd_diff({src}, window_slow={slow}, window_fast={fast}, window_sign={signal})"


def _atr(args: list[str], kwargs: dict[str, str]) -> str:
    length = args[0] if args else kwargs.get("length", "14")
    return f"ta.volatility.average_true_range(df['high'], df['low'], df['close'], window={length})"


def _stoch(args: list[str], kwargs: dict[str, str]) -> str:
    k = args[3] if len(args) > 3 else kwargs.get("length", kwargs.get("k", "14"))
    return f"ta.momentum.stoch(df['high'], df['low'], df['close'], window={k})"


def _vwma(args: list[str], kwargs: dict[str, str]) -> str:
    src = args[0] if args else kwargs.get("source", "df['close']")
    length = args[1] if len(args) > 1 else kwargs.get("length", "14")
    return f"ta.volume.volume_weighted_average_price(df['high'], df['low'], {src}, df['volume'], window={length})"


def _crossover(args: list[str], kwargs: dict[str, str]) -> str:
    a = args[0] if args else "a"
    b = args[1] if len(args) > 1 else "b"
    return f"({a} > {b}) & ({a}.shift(1) <= {b}.shift(1))"


def _crossunder(args: list[str], kwargs: dict[str, str]) -> str:
    a = args[0] if args else "a"
    b = args[1] if len(args) > 1 else "b"
    return f"({a} < {b}) & ({a}.shift(1) >= {b}.shift(1))"


def _highest(args: list[str], kwargs: dict[str, str]) -> str:
    src = args[0] if args else kwargs.get("source", "df['close']")
    length = args[1] if len(args) > 1 else kwargs.get("length", "14")
    return f"{src}.rolling({length}).max()"


def _lowest(args: list[str], kwargs: dict[str, str]) -> str:
    src = args[0] if args else kwargs.get("source", "df['close']")
    length = args[1] if len(args) > 1 else kwargs.get("length", "14")
    return f"{src}.rolling({length}).min()"


def _change(args: list[str], kwargs: dict[str, str]) -> str:
    src = args[0] if args else kwargs.get("source", "df['close']")
    return f"{src}.diff()"


def _cum(args: list[str], kwargs: dict[str, str]) -> str:
    src = args[0] if args else kwargs.get("source", "df['close']")
    return f"{src}.cumsum()"


def _na(args: list[str], kwargs: dict[str, str]) -> str:
    x = args[0] if args else "x"
    return f"pd.isna({x})"


def _nz(args: list[str], kwargs: dict[str, str]) -> str:
    x = args[0] if args else "x"
    val = args[1] if len(args) > 1 else kwargs.get("val", "0")
    return f"{x}.fillna({val})"


def _wma(args: list[str], kwargs: dict[str, str]) -> str:
    src = args[0] if args else kwargs.get("source", "df['close']")
    length = args[1] if len(args) > 1 else kwargs.get("length", "14")
    return f"ta.trend.wma_indicator({src}, window={length})"


def _hma(args: list[str], kwargs: dict[str, str]) -> str:
    # ta library doesn't have HMA directly — approximate with WMA composition
    src = args[0] if args else kwargs.get("source", "df['close']")
    length = args[1] if len(args) > 1 else kwargs.get("length", "14")
    return f"ta.trend.wma_indicator({src}, window={length})  # HMA approximation"


def _bb_upper(args: list[str], kwargs: dict[str, str]) -> str:
    src = args[0] if args else kwargs.get("source", "df['close']")
    length = args[1] if len(args) > 1 else kwargs.get("length", "20")
    std = args[2] if len(args) > 2 else kwargs.get("mult", kwargs.get("std", "2"))
    return f"ta.volatility.bollinger_hband({src}, window={length}, window_dev={std})"


def _bb_mid(args: list[str], kwargs: dict[str, str]) -> str:
    src = args[0] if args else kwargs.get("source", "df['close']")
    length = args[1] if len(args) > 1 else kwargs.get("length", "20")
    return f"ta.volatility.bollinger_mavg({src}, window={length})"


def _bb_lower(args: list[str], kwargs: dict[str, str]) -> str:
    src = args[0] if args else kwargs.get("source", "df['close']")
    length = args[1] if len(args) > 1 else kwargs.get("length", "20")
    std = args[2] if len(args) > 2 else kwargs.get("mult", kwargs.get("std", "2"))
    return f"ta.volatility.bollinger_lband({src}, window={length}, window_dev={std})"


def _cci(args: list[str], kwargs: dict[str, str]) -> str:
    length = args[0] if args else kwargs.get("length", "20")
    return f"ta.trend.cci(df['high'], df['low'], df['close'], window={length})"


def _mfi(args: list[str], kwargs: dict[str, str]) -> str:
    length = args[0] if args else kwargs.get("length", "14")
    return f"ta.volume.money_flow_index(df['high'], df['low'], df['close'], df['volume'], window={length})"


def _obv(args: list[str], kwargs: dict[str, str]) -> str:
    return "ta.volume.on_balance_volume(df['close'], df['volume'])"


def _adx(args: list[str], kwargs: dict[str, str]) -> str:
    length = args[0] if args else kwargs.get("length", "14")
    return f"ta.trend.adx(df['high'], df['low'], df['close'], window={length})"


# ═══════════════════════════════════════════════
# MASTER MAPPING TABLE
# ═══════════════════════════════════════════════

INDICATOR_MAP: dict[str, IndicatorMapping] = {
    # Moving Averages
    "ta.sma": IndicatorMapping("ta.sma", _sma, notes="Simple Moving Average"),
    "ta.ema": IndicatorMapping("ta.ema", _ema, notes="Exponential Moving Average"),
    "ta.wma": IndicatorMapping("ta.wma", _wma, notes="Weighted Moving Average"),
    "ta.hma": IndicatorMapping("ta.hma", _hma, notes="Hull Moving Average (WMA approx)"),
    "ta.vwma": IndicatorMapping("ta.vwma", _vwma, notes="Volume Weighted Average Price"),

    # Oscillators
    "ta.rsi": IndicatorMapping("ta.rsi", _rsi, notes="Relative Strength Index"),
    "ta.macd": IndicatorMapping("ta.macd", _macd, notes="MACD (returns 3 components)", output_type="multi_column", unpack_columns=["macd", "signal", "hist"]),
    "ta.stoch": IndicatorMapping("ta.stoch", _stoch, needs_ohlc=True, notes="Stochastic Oscillator"),
    "ta.cci": IndicatorMapping("ta.cci", _cci, needs_ohlc=True, notes="Commodity Channel Index"),
    "ta.mfi": IndicatorMapping("ta.mfi", _mfi, needs_ohlc=True, notes="Money Flow Index"),
    "ta.adx": IndicatorMapping("ta.adx", _adx, needs_ohlc=True, notes="Average Directional Index"),

    # Volatility
    "ta.atr": IndicatorMapping("ta.atr", _atr, needs_ohlc=True, notes="Average True Range"),
    "ta.bb": IndicatorMapping("ta.bb", _bb_upper, notes="Bollinger Bands upper"),
    "ta.bbands": IndicatorMapping("ta.bbands", _bb_upper, notes="Bollinger Bands alias"),

    # Volume
    "ta.obv": IndicatorMapping("ta.obv", _obv, needs_ohlc=True, notes="On-Balance Volume"),

    # Cross detection
    "ta.crossover": IndicatorMapping("ta.crossover", _crossover, notes="Bullish crossover (a crosses above b)"),
    "ta.crossunder": IndicatorMapping("ta.crossunder", _crossunder, notes="Bearish crossunder (a crosses below b)"),

    # Rolling aggregates
    "ta.highest": IndicatorMapping("ta.highest", _highest, notes="Rolling maximum"),
    "ta.lowest": IndicatorMapping("ta.lowest", _lowest, notes="Rolling minimum"),

    # Transforms
    "ta.change": IndicatorMapping("ta.change", _change, notes="Period-over-period change"),
    "ta.cum": IndicatorMapping("ta.cum", _cum, notes="Cumulative sum"),

    # Utilities
    "na": IndicatorMapping("na", _na, notes="Check for NaN/null"),
    "nz": IndicatorMapping("nz", _nz, notes="Replace NaN with value"),
}


# ═══════════════════════════════════════════════
# BUILT-IN VARIABLE MAPPINGS
# ═══════════════════════════════════════════════

BUILTIN_VARS: dict[str, str] = {
    "close": "df['close']",
    "open": "df['open']",
    "high": "df['high']",
    "low": "df['low']",
    "volume": "df['volume']",
    "bar_index": "df.index",
    "hlc3": "(df['high'] + df['low'] + df['close']) / 3",
    "hl2": "(df['high'] + df['low']) / 2",
    "ohlc4": "(df['open'] + df['high'] + df['low'] + df['close']) / 4",
    "src": "df['close']",  # common alias
}


def resolve_indicator(pine_func: str, args: list[str], kwargs: dict[str, str]) -> str | None:
    """
    Resolve a Pine Script ta.* call to its Python equivalent.

    Args:
        pine_func: The Pine Script function name (e.g., "ta.sma")
        args: Positional arguments as strings
        kwargs: Keyword arguments as strings

    Returns:
        Python code string, or None if unsupported.
    """
    mapping = INDICATOR_MAP.get(pine_func)
    if mapping is None:
        return None

    # Substitute Pine built-in variables in args
    resolved_args = [_resolve_builtins(a) for a in args]
    resolved_kwargs = {k: _resolve_builtins(v) for k, v in kwargs.items()}

    return mapping.python_expr(resolved_args, resolved_kwargs)


def _resolve_builtins(expr: str) -> str:
    """Replace Pine Script built-in variable names with DataFrame column references."""
    result = expr
    for pine_var, py_expr in BUILTIN_VARS.items():
        # Only replace whole-word matches
        if result == pine_var:
            return py_expr
    return result


def get_supported_functions() -> list[dict[str, str]]:
    """Get list of supported functions for the CLI 'supported' command."""
    return [
        {
            "pine_name": m.pine_name,
            "notes": m.notes,
            "needs_ohlc": str(m.needs_ohlc),
        }
        for m in INDICATOR_MAP.values()
    ]

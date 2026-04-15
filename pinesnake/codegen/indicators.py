"""
PineSnake Indicator Mappings — ta.* → pandas-ta / pandas equivalents.

This module defines how Pine Script's ta.* functions map to their
Python equivalents. The code generator uses this table to produce
correct pandas-ta / pandas code in the output script.
"""

from __future__ import annotations

from dataclasses import dataclass
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


def _sma(args: list[str], kwargs: dict[str, str]) -> str:
    src = args[0] if args else kwargs.get("source", "df['close']")
    length = args[1] if len(args) > 1 else kwargs.get("length", "14")
    return f"ta.sma({src}, length={length})"


def _ema(args: list[str], kwargs: dict[str, str]) -> str:
    src = args[0] if args else kwargs.get("source", "df['close']")
    length = args[1] if len(args) > 1 else kwargs.get("length", "14")
    return f"ta.ema({src}, length={length})"


def _rsi(args: list[str], kwargs: dict[str, str]) -> str:
    src = args[0] if args else kwargs.get("source", "df['close']")
    length = args[1] if len(args) > 1 else kwargs.get("length", "14")
    return f"ta.rsi({src}, length={length})"


def _macd(args: list[str], kwargs: dict[str, str]) -> str:
    src = args[0] if args else kwargs.get("source", "df['close']")
    fast = args[1] if len(args) > 1 else kwargs.get("fast", "12")
    slow = args[2] if len(args) > 2 else kwargs.get("slow", "26")
    signal = args[3] if len(args) > 3 else kwargs.get("signal", "9")
    return f"ta.macd({src}, fast={fast}, slow={slow}, signal={signal})"


def _atr(args: list[str], kwargs: dict[str, str]) -> str:
    length = args[0] if args else kwargs.get("length", "14")
    return f"ta.atr(df['high'], df['low'], df['close'], length={length})"


def _stoch(args: list[str], kwargs: dict[str, str]) -> str:
    k = args[3] if len(args) > 3 else kwargs.get("length", kwargs.get("k", "14"))
    return f"ta.stoch(df['high'], df['low'], df['close'], k={k})"


def _vwma(args: list[str], kwargs: dict[str, str]) -> str:
    src = args[0] if args else kwargs.get("source", "df['close']")
    length = args[1] if len(args) > 1 else kwargs.get("length", "14")
    return f"ta.vwma({src}, df['volume'], length={length})"


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
    return f"ta.wma({src}, length={length})"


def _hma(args: list[str], kwargs: dict[str, str]) -> str:
    src = args[0] if args else kwargs.get("source", "df['close']")
    length = args[1] if len(args) > 1 else kwargs.get("length", "14")
    return f"ta.hma({src}, length={length})"


def _bb(args: list[str], kwargs: dict[str, str]) -> str:
    src = args[0] if args else kwargs.get("source", "df['close']")
    length = args[1] if len(args) > 1 else kwargs.get("length", "20")
    std = args[2] if len(args) > 2 else kwargs.get("mult", kwargs.get("std", "2.0"))
    return f"ta.bbands({src}, length={length}, std={std})"


def _cci(args: list[str], kwargs: dict[str, str]) -> str:
    length = args[0] if args else kwargs.get("length", "20")
    return f"ta.cci(df['high'], df['low'], df['close'], length={length})"


def _mfi(args: list[str], kwargs: dict[str, str]) -> str:
    length = args[0] if args else kwargs.get("length", "14")
    return f"ta.mfi(df['high'], df['low'], df['close'], df['volume'], length={length})"


def _obv(args: list[str], kwargs: dict[str, str]) -> str:
    return "ta.obv(df['close'], df['volume'])"


def _adx(args: list[str], kwargs: dict[str, str]) -> str:
    length = args[0] if args else kwargs.get("length", "14")
    return f"ta.adx(df['high'], df['low'], df['close'], length={length})"


# ═══════════════════════════════════════════════
# MASTER MAPPING TABLE
# ═══════════════════════════════════════════════

INDICATOR_MAP: dict[str, IndicatorMapping] = {
    # Moving Averages
    "ta.sma": IndicatorMapping("ta.sma", _sma, notes="Simple Moving Average"),
    "ta.ema": IndicatorMapping("ta.ema", _ema, notes="Exponential Moving Average"),
    "ta.wma": IndicatorMapping("ta.wma", _wma, notes="Weighted Moving Average"),
    "ta.hma": IndicatorMapping("ta.hma", _hma, notes="Hull Moving Average"),
    "ta.vwma": IndicatorMapping("ta.vwma", _vwma, notes="Volume Weighted Moving Average"),

    # Oscillators
    "ta.rsi": IndicatorMapping("ta.rsi", _rsi, notes="Relative Strength Index"),
    "ta.macd": IndicatorMapping("ta.macd", _macd, notes="MACD (returns DataFrame with 3 cols)", output_type="multi_column", unpack_columns=["macd", "signal", "hist"]),
    "ta.stoch": IndicatorMapping("ta.stoch", _stoch, needs_ohlc=True, notes="Stochastic Oscillator", output_type="multi_column", unpack_columns=["k", "d"]),
    "ta.cci": IndicatorMapping("ta.cci", _cci, needs_ohlc=True, notes="Commodity Channel Index"),
    "ta.mfi": IndicatorMapping("ta.mfi", _mfi, needs_ohlc=True, notes="Money Flow Index"),
    "ta.adx": IndicatorMapping("ta.adx", _adx, needs_ohlc=True, notes="Average Directional Index"),

    # Volatility
    "ta.atr": IndicatorMapping("ta.atr", _atr, needs_ohlc=True, notes="Average True Range"),
    "ta.bb": IndicatorMapping("ta.bb", _bb, notes="Bollinger Bands (returns DataFrame)", output_type="multi_column", unpack_columns=["lower", "mid", "upper", "bandwidth", "percent"]),
    "ta.bbands": IndicatorMapping("ta.bbands", _bb, notes="Bollinger Bands alias", output_type="multi_column", unpack_columns=["lower", "mid", "upper", "bandwidth", "percent"]),

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

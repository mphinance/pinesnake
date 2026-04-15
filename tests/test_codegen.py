"""Tests for the PineSnake code generator module."""

import pytest
from pathlib import Path

from pinesnake.parser import parse_pine
from pinesnake.analyzer import analyze
from pinesnake.codegen.generator import CodeGenerator, generate, generate_env
from pinesnake.codegen.indicators import (
    resolve_indicator,
    get_supported_functions,
    INDICATOR_MAP,
)


EXAMPLES_DIR = Path(__file__).parent.parent / "examples"


class TestIndicatorResolution:
    """Test indicator mapping resolution."""

    def test_sma(self):
        result = resolve_indicator("ta.sma", ["df['close']", "14"], {})
        assert result is not None
        assert "ta.sma" in result
        assert "14" in result

    def test_ema(self):
        result = resolve_indicator("ta.ema", ["df['close']", "21"], {})
        assert result is not None
        assert "ta.ema" in result

    def test_rsi(self):
        result = resolve_indicator("ta.rsi", ["df['close']", "14"], {})
        assert result is not None
        assert "ta.rsi" in result

    def test_macd(self):
        result = resolve_indicator("ta.macd", ["df['close']", "12", "26", "9"], {})
        assert result is not None
        assert "ta.macd" in result

    def test_atr(self):
        result = resolve_indicator("ta.atr", ["14"], {})
        assert result is not None
        assert "high" in result and "low" in result

    def test_crossover(self):
        result = resolve_indicator("ta.crossover", ["fast", "slow"], {})
        assert result is not None
        assert ">" in result and "shift" in result

    def test_crossunder(self):
        result = resolve_indicator("ta.crossunder", ["fast", "slow"], {})
        assert result is not None
        assert "<" in result and "shift" in result

    def test_unsupported(self):
        result = resolve_indicator("ta.nonexistent", [], {})
        assert result is None

    def test_all_mappings_callable(self):
        """Every mapping should be callable and produce output."""
        for name, mapping in INDICATOR_MAP.items():
            result = mapping.python_expr(["df['close']", "14"], {})
            assert isinstance(result, str), f"{name} did not return string"
            assert len(result) > 0, f"{name} returned empty string"


class TestSupportedFunctions:
    """Test the supported functions listing."""

    def test_returns_list(self):
        funcs = get_supported_functions()
        assert isinstance(funcs, list)
        assert len(funcs) > 15  # We have 20+ mappings

    def test_has_required_keys(self):
        funcs = get_supported_functions()
        for func in funcs:
            assert "pine_name" in func
            assert "notes" in func


class TestCodeGeneration:
    """Test end-to-end code generation."""

    def test_generate_rsi(self):
        """Generate Python code from RSI strategy."""
        tree = parse_pine(EXAMPLES_DIR / "rsi_strategy.pine")
        spec = analyze(tree)
        code = generate(spec, timeframe="5min", symbol="SPY")

        assert len(code) > 100
        assert "pandas_ta" in code or "ta." in code
        assert "TRADIER" in code
        assert "DRY_RUN" in code
        assert "def main" in code

    def test_generate_ema(self):
        """Generate Python code from EMA crossover strategy."""
        tree = parse_pine(EXAMPLES_DIR / "ema_crossover.pine")
        spec = analyze(tree)
        code = generate(spec, timeframe="5min", symbol="SPY")

        assert "ema" in code.lower()
        assert "def calculate_indicators" in code
        assert "def check_signals" in code

    def test_generate_env_file(self):
        """Generate .env config file."""
        tree = parse_pine(EXAMPLES_DIR / "rsi_strategy.pine")
        spec = analyze(tree)
        env = generate_env(spec, timeframe="5min", symbol="SPY")

        assert "TRADIER_API_KEY" in env
        assert "DRY_RUN=true" in env
        assert "SPY" in env

    def test_generated_code_has_safety(self):
        """Generated code should have DRY_RUN safety by default."""
        tree = parse_pine(EXAMPLES_DIR / "rsi_strategy.pine")
        spec = analyze(tree)
        code = generate(spec)

        assert "DRY_RUN" in code
        assert "DRY RUN" in code  # Log message
        assert "true" in code  # Default value

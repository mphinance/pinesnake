"""Tests for the PineSnake analyzer module."""

import pytest
from pathlib import Path

from pinesnake.parser import parse_pine, parse_pine_string
from pinesnake.analyzer import (
    Analyzer,
    StrategySpec,
    InputType,
    Direction,
    StrategyAction,
    analyze,
    _to_env_key,
)


EXAMPLES_DIR = Path(__file__).parent.parent / "examples"


class TestEnvKeyConversion:
    """Test variable name → ENV key conversion."""

    def test_camel_case(self):
        assert _to_env_key("fastLength") == "FAST_LENGTH"

    def test_title_case_spaces(self):
        assert _to_env_key("Fast Length") == "FAST_LENGTH"

    def test_snake_case(self):
        assert _to_env_key("rsi_period") == "RSI_PERIOD"

    def test_all_upper(self):
        assert _to_env_key("RSI") == "RSI"

    def test_mixed(self):
        assert _to_env_key("myMACD_fast") == "MY_MACD_FAST"


class TestAnalyzeRSI:
    """Test analyzing the RSI example strategy."""

    @pytest.fixture
    def spec(self) -> StrategySpec:
        tree = parse_pine(EXAMPLES_DIR / "rsi_strategy.pine")
        return analyze(tree, source_file="rsi_strategy.pine")

    def test_strategy_name(self, spec):
        assert "RSI" in spec.name

    def test_inputs_detected(self, spec):
        assert len(spec.inputs) >= 1  # At least RSI length

    def test_input_types(self, spec):
        for inp in spec.inputs:
            assert inp.input_type in (InputType.INT, InputType.FLOAT, InputType.BOOL)

    def test_indicators_detected(self, spec):
        assert len(spec.indicators) >= 1
        pine_funcs = [i.pine_func for i in spec.indicators]
        assert any("rsi" in f for f in pine_funcs)

    def test_strategy_calls_detected(self, spec):
        assert len(spec.strategy_calls) >= 1
        actions = [sc.action for sc in spec.strategy_calls]
        assert StrategyAction.ENTRY in actions

    def test_summary_not_empty(self, spec):
        summary = spec.summary()
        assert len(summary) > 0
        assert "RSI" in summary


class TestAnalyzeEMA:
    """Test analyzing the EMA crossover example strategy."""

    @pytest.fixture
    def spec(self) -> StrategySpec:
        tree = parse_pine(EXAMPLES_DIR / "ema_crossover.pine")
        return analyze(tree, source_file="ema_crossover.pine")

    def test_strategy_name(self, spec):
        assert "EMA" in spec.name

    def test_two_inputs(self, spec):
        assert len(spec.inputs) >= 2
        names = [i.name for i in spec.inputs]
        assert any("fast" in n.lower() for n in names)
        assert any("slow" in n.lower() for n in names)

    def test_two_indicators(self, spec):
        assert len(spec.indicators) >= 2
        pine_funcs = [i.pine_func for i in spec.indicators]
        assert all("ema" in f for f in pine_funcs)


class TestAnalyzeMACD:
    """Test analyzing the MACD example strategy."""

    @pytest.fixture
    def spec(self) -> StrategySpec:
        tree = parse_pine(EXAMPLES_DIR / "macd_strategy.pine")
        return analyze(tree, source_file="macd_strategy.pine")

    def test_strategy_name(self, spec):
        assert "MACD" in spec.name

    def test_inputs(self, spec):
        assert len(spec.inputs) >= 3  # fast, slow, signal

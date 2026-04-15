"""Tests for the PineSnake parser module."""

import pytest
from pathlib import Path

from pinesnake.parser import parse_pine, parse_pine_string, ParseError, dump_ast


EXAMPLES_DIR = Path(__file__).parent.parent / "examples"


class TestParseFile:
    """Test parsing Pine Script files from disk."""

    def test_parse_rsi_strategy(self):
        """Parse the RSI example strategy."""
        tree = parse_pine(EXAMPLES_DIR / "rsi_strategy.pine")
        assert tree is not None
        assert hasattr(tree, "body") or hasattr(tree, "statements")

    def test_parse_ema_crossover(self):
        """Parse the EMA crossover example strategy."""
        tree = parse_pine(EXAMPLES_DIR / "ema_crossover.pine")
        assert tree is not None

    def test_parse_macd_strategy(self):
        """Parse the MACD example strategy."""
        tree = parse_pine(EXAMPLES_DIR / "macd_strategy.pine")
        assert tree is not None

    def test_file_not_found(self):
        """Raise FileNotFoundError for missing files."""
        with pytest.raises(FileNotFoundError):
            parse_pine("nonexistent.pine")


class TestParseString:
    """Test parsing Pine Script source strings."""

    def test_simple_strategy(self):
        """Parse a minimal strategy declaration."""
        source = '''
//@version=5
strategy("Test", overlay=true)
close
'''
        tree = parse_pine_string(source)
        assert tree is not None

    def test_empty_source(self):
        """Raise ParseError on empty input."""
        with pytest.raises(ParseError):
            parse_pine_string("")

    def test_whitespace_only(self):
        """Raise ParseError on whitespace-only input."""
        with pytest.raises(ParseError):
            parse_pine_string("   \n\n  ")

    def test_parse_with_indicators(self):
        """Parse source with ta.* indicators."""
        source = '''
//@version=5
strategy("Test RSI", overlay=true)
rsiVal = ta.rsi(close, 14)
'''
        tree = parse_pine_string(source)
        assert tree is not None


class TestDumpAST:
    """Test AST debug dump utility."""

    def test_dump_produces_output(self):
        """dump_ast should produce non-empty string output."""
        tree = parse_pine(EXAMPLES_DIR / "rsi_strategy.pine")
        output = dump_ast(tree)
        assert len(output) > 0
        assert "Script" in output

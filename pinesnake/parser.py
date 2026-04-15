"""
PineSnake Parser — Wraps pynescript to produce an AST from Pine Script v5 source.

Usage:
    from pinesnake.parser import parse_pine
    ast = parse_pine("path/to/strategy.pine")
    ast = parse_pine_string(source_code)
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from pynescript import ast as pine_ast
from pynescript.ast import parse as pine_parse

logger = logging.getLogger(__name__)


class ParseError(Exception):
    """Raised when Pine Script source cannot be parsed."""

    def __init__(self, message: str, source_file: str | None = None):
        self.source_file = source_file
        super().__init__(message)


def parse_pine(filepath: str | Path) -> pine_ast.Script:
    """
    Parse a Pine Script v5 file into an AST.

    Args:
        filepath: Path to a .pine file.

    Returns:
        pynescript Script AST node.

    Raises:
        ParseError: If the file cannot be read or parsed.
        FileNotFoundError: If the file does not exist.
    """
    filepath = Path(filepath)
    if not filepath.exists():
        raise FileNotFoundError(f"Pine Script file not found: {filepath}")

    if not filepath.suffix == ".pine":
        logger.warning(f"File does not have .pine extension: {filepath}")

    source = filepath.read_text(encoding="utf-8")
    logger.info(f"Parsing Pine Script: {filepath.name} ({len(source)} chars)")

    return parse_pine_string(source, source_file=str(filepath))


def parse_pine_string(source: str, source_file: str | None = None) -> pine_ast.Script:
    """
    Parse Pine Script v5 source code string into an AST.

    Args:
        source: Pine Script v5 source code.
        source_file: Optional filename for error messages.

    Returns:
        pynescript Script AST node.

    Raises:
        ParseError: If the source cannot be parsed.
    """
    if not source or not source.strip():
        raise ParseError("Empty source code", source_file=source_file)

    try:
        tree = pine_parse(source)
    except Exception as e:
        raise ParseError(
            f"Failed to parse Pine Script: {e}",
            source_file=source_file,
        ) from e

    if tree is None:
        raise ParseError("Parser returned None", source_file=source_file)

    logger.info(f"AST parsed successfully — {_count_nodes(tree)} nodes")
    return tree


def _count_nodes(node: Any, _depth: int = 0) -> int:
    """Recursively count AST nodes for logging."""
    count = 1
    if _depth > 100:  # guard against pathological recursion
        return count
    if hasattr(node, "__dict__"):
        for value in node.__dict__.values():
            if isinstance(value, list):
                for item in value:
                    count += _count_nodes(item, _depth + 1)
            elif hasattr(value, "__dict__"):
                count += _count_nodes(value, _depth + 1)
    return count


def dump_ast(node: Any, indent: int = 0) -> str:
    """
    Pretty-print an AST node tree for debugging.

    Args:
        node: AST node from pynescript.
        indent: Current indentation level.

    Returns:
        Multi-line string representation of the AST.
    """
    prefix = "  " * indent
    lines = [f"{prefix}{type(node).__name__}"]

    if hasattr(node, "__dict__"):
        for key, value in node.__dict__.items():
            if key.startswith("_"):
                continue
            if isinstance(value, list):
                lines.append(f"{prefix}  {key}:")
                for item in value:
                    if hasattr(item, "__dict__"):
                        lines.append(dump_ast(item, indent + 2))
                    else:
                        lines.append(f"{prefix}    {repr(item)}")
            elif hasattr(value, "__dict__"):
                lines.append(f"{prefix}  {key}:")
                lines.append(dump_ast(value, indent + 2))
            else:
                lines.append(f"{prefix}  {key}: {repr(value)}")

    return "\n".join(lines)

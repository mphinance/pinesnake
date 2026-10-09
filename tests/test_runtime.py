"""Execute the expressions PineSnake emits. String-match tests can't catch a call
the `ta` library rejects (e.g. a bad kwarg), so run each mapping on real data."""

import numpy as np
import pandas as pd
import pytest
import ta  # noqa: F401  (generated code refers to `ta` and `pd` by name)

from pinesnake.codegen.indicators import INDICATOR_MAP, resolve_indicator


@pytest.fixture(scope="module")
def df():
    rng = np.random.default_rng(7)
    close = 100 + np.cumsum(rng.normal(0, 1, 300))
    return pd.DataFrame({
        "open": close + rng.normal(0, 0.2, 300),
        "high": close + 1,
        "low": close - 1,
        "close": close,
        "volume": rng.integers(1_000, 5_000, 300).astype(float),
    })


ARGS = {
    "ta.sma": ["close", "10"], "ta.ema": ["close", "10"],
    "ta.wma": ["close", "10"], "ta.hma": ["close", "16"],
    "ta.vwma": ["close", "10"], "ta.rsi": ["close", "14"],
    "ta.macd": ["close", "12", "26", "9"], "ta.stoch": ["close", "high", "low", "14"],
    "ta.cci": ["20"], "ta.mfi": ["14"], "ta.adx": ["14"], "ta.atr": ["14"],
    "ta.bb": ["close", "20", "2"], "ta.bbands": ["close", "20", "2"],
    "ta.obv": [], "ta.highest": ["close", "10"], "ta.lowest": ["close", "10"],
    "ta.change": ["close"], "ta.cum": ["close"],
    "na": ["close"], "nz": ["close", "0"],
}


def test_every_indicator_has_a_runtime_case():
    assert set(ARGS) == set(INDICATOR_MAP)


@pytest.mark.parametrize("name", sorted(INDICATOR_MAP))
def test_expression_executes(name, df):
    out = eval(resolve_indicator(name, ARGS[name], {}), {"df": df, "ta": ta, "pd": pd})
    mapping = INDICATOR_MAP[name]
    if mapping.output_type == "multi_column":
        assert isinstance(out, pd.DataFrame)
        assert list(out.columns) == mapping.unpack_columns
        assert out.iloc[-1].notna().all()
    else:
        assert len(out) == len(df)


def test_macd_hist_is_line_minus_signal(df):
    out = eval(resolve_indicator("ta.macd", ARGS["ta.macd"], {}), {"df": df, "ta": ta, "pd": pd})
    assert np.allclose(out["hist"].dropna(), (out["macd"] - out["signal"]).dropna())


def test_bollinger_bands_bracket_basis(df):
    out = eval(resolve_indicator("ta.bb", ARGS["ta.bb"], {}), {"df": df, "ta": ta, "pd": pd}).dropna()
    assert (out["lower"] < out["basis"]).all() and (out["basis"] < out["upper"]).all()


def test_vwma_matches_definition(df):
    out = eval(resolve_indicator("ta.vwma", ARGS["ta.vwma"], {}), {"df": df, "ta": ta, "pd": pd})
    i = len(df) - 1
    w = df.iloc[i - 9:i + 1]
    assert out.iloc[-1] == pytest.approx((w["close"] * w["volume"]).sum() / w["volume"].sum())


def test_hma_differs_from_plain_wma(df):
    hma = eval(resolve_indicator("ta.hma", ARGS["ta.hma"], {}), {"df": df, "ta": ta, "pd": pd})
    wma = eval(resolve_indicator("ta.wma", ["close", "16"], {}), {"df": df, "ta": ta, "pd": pd})
    assert not np.allclose(hma.dropna().iloc[-20:], wma.iloc[-20:])

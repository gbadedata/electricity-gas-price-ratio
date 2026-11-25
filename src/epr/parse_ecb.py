"""Parse ECB monthly euro reference rates and average them by semester."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from .paths import RAW


def parse_monthly(path: Path = RAW / "ecb_exr_monthly.csv") -> pd.DataFrame:
    df = pd.read_csv(path, dtype=str, keep_default_na=False)
    need = {"CURRENCY", "CURRENCY_DENOM", "TIME_PERIOD", "OBS_VALUE", "EXR_TYPE", "EXR_SUFFIX"}
    missing = need - set(df.columns)
    if missing:
        raise ValueError(f"ECB file missing columns {sorted(missing)}")
    if set(df["CURRENCY_DENOM"]) != {"EUR"} or set(df["EXR_TYPE"]) != {"SP00"} or set(df["EXR_SUFFIX"]) != {"A"}:
        raise ValueError("ECB file is not monthly-average units of currency per euro")
    out = pd.DataFrame({
        "currency": df["CURRENCY"],
        "month": df["TIME_PERIOD"],
        "per_eur": pd.to_numeric(df["OBS_VALUE"], errors="coerce"),
    }).dropna()
    return out


def semester_average(monthly: pd.DataFrame) -> pd.DataFrame:
    """Simple mean of the six monthly averages in each half-year.

    Eurostat converts national-currency prices to euro with the average rate
    for the semester; the FX cross-check tests whether that holds.
    """
    m = monthly.copy()
    year = m["month"].str[:4]
    mon = m["month"].str[5:7].astype(int)
    m["period"] = year + "-S" + (1 + (mon > 6)).astype(str)
    g = m.groupby(["currency", "period"])
    out = g["per_eur"].mean().rename("per_eur").to_frame()
    out["months"] = g.size()
    out = out.reset_index()
    return out[out["months"] == 6].drop(columns="months").reset_index(drop=True)

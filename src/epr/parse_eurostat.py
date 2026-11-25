"""Parse Eurostat SDMX-CSV extracts into one tidy price table."""

from __future__ import annotations

import re
from pathlib import Path

import pandas as pd

from .paths import RAW

# Eurostat consumption-band codes -> short band names used in the dataset.
ELECTRICITY_BANDS = {
    "KWH_LT1000": "DA",
    "KWH1000-2499": "DB",
    "KWH2500-4999": "DC",
    "KWH5000-14999": "DD",
    "KWH_GE15000": "DE",
    "TOT_KWH": "ALL",
}
GAS_BANDS = {
    "GJ_LT20": "D1",
    "GJ20-199": "D2",
    "GJ_GE200": "D3",
    "TOT_GJ": "ALL",
}

PERIOD_RE = re.compile(r"^\d{4}-S[12]$")

TIDY_COLUMNS = [
    "geo", "period", "fuel", "band", "tax", "currency",
    "price_per_kwh", "flag", "source_id", "source_last_update",
]


def _read(path: Path) -> pd.DataFrame:
    return pd.read_csv(path, dtype=str, keep_default_na=False)


def parse_prices(path: Path, fuel: str, source_id: str) -> pd.DataFrame:
    """Semester household prices (nrg_pc_204 / nrg_pc_202) -> tidy rows.

    Only the 2007-S2 onward methodology (bands DA-DE, D1-D3) is kept; the
    pre-2007 "standard consumer" bands measure something different.
    """
    df = _read(path)
    bands = ELECTRICITY_BANDS if fuel == "electricity" else GAS_BANDS
    unknown_cols = {"geo", "TIME_PERIOD", "OBS_VALUE", "OBS_FLAG", "nrg_cons", "tax", "currency", "unit"} - set(df.columns)
    if unknown_cols:
        raise ValueError(f"{path.name}: missing columns {sorted(unknown_cols)}")

    df = df[df["nrg_cons"].isin(bands)].copy()
    if (df["unit"] != "KWH").any():
        raise ValueError(f"{path.name}: unexpected units {sorted(df['unit'].unique())}")
    if fuel == "gas" and (df["freq"] != "S").any():
        raise ValueError(f"{path.name}: expected semester data only")

    out = pd.DataFrame({
        "geo": df["geo"],
        "period": df["TIME_PERIOD"],
        "fuel": fuel,
        "band": df["nrg_cons"].map(bands),
        "tax": df["tax"],
        "currency": df["currency"],
        "price_per_kwh": pd.to_numeric(df["OBS_VALUE"].replace("", None), errors="coerce"),
        "flag": df["OBS_FLAG"],
        "source_id": source_id,
        "source_last_update": df["LAST UPDATE"],
    })
    bad = ~out["period"].str.match(PERIOD_RE)
    if bad.any():
        raise ValueError(f"{path.name}: unexpected periods {sorted(out.loc[bad, 'period'].unique())[:5]}")
    return out[TIDY_COLUMNS].reset_index(drop=True)


def parse_components(path: Path, fuel: str, source_id: str) -> pd.DataFrame:
    """Annual price components (nrg_pc_204_c / nrg_pc_202_c) -> tidy rows."""
    df = _read(path)
    bands = ELECTRICITY_BANDS if fuel == "electricity" else GAS_BANDS
    df = df[df["nrg_cons"].isin(bands)].copy()
    return pd.DataFrame({
        "geo": df["geo"],
        "year": df["TIME_PERIOD"].astype(int),
        "fuel": fuel,
        "band": df["nrg_cons"].map(bands),
        "component": df["nrg_prc"],
        "currency": df["currency"],
        "value_per_kwh": pd.to_numeric(df["OBS_VALUE"].replace("", None), errors="coerce"),
        "flag": df["OBS_FLAG"],
        "source_id": source_id,
    }).reset_index(drop=True)


def load_all(raw: Path = RAW) -> tuple[pd.DataFrame, pd.DataFrame]:
    prices = pd.concat([
        parse_prices(raw / "nrg_pc_204.csv", "electricity", "eurostat_nrg_pc_204"),
        parse_prices(raw / "nrg_pc_202.csv", "gas", "eurostat_nrg_pc_202"),
    ], ignore_index=True)
    components = pd.concat([
        parse_components(raw / "nrg_pc_204_c.csv", "electricity", "eurostat_nrg_pc_204_c"),
        parse_components(raw / "nrg_pc_202_c.csv", "gas", "eurostat_nrg_pc_202_c"),
    ], ignore_index=True)
    return prices, components

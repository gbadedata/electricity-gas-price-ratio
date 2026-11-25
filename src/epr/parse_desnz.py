"""Parse the DESNZ workbooks that carry UK prices after the UK left Eurostat.

Two kinds of table are read:

* QEP 5.6.x (electricity) and 5.10.x (gas): UK household prices collected by
  DESNZ "using the same methodology" as Eurostat, by consumption band and
  semester, in pence per kWh. These continue the UK series after Eurostat's
  last UK observation (2020-S1).
* QEP 2.2.4 (electricity) and 2.3.4 (gas): calendar-year average unit rate
  (GBP/kWh) and fixed cost (GBP/year) for standard tariffs. These are an
  independent DESNZ series used to cross-check the semester figures and to
  compare a marginal (unit-rate) ratio with an average-price ratio.
"""

from __future__ import annotations

from pathlib import Path

import openpyxl
import pandas as pd

from .paths import RAW

PERIOD_MAP = {"Jan – Jun": "1", "Jul – Dec": "2", "Jan - Jun": "1", "Jul - Dec": "2"}

# (file, sheet, fuel, band, tax)
EU_FORMAT_SHEETS = [
    ("qep_561.xlsx", "5.6.2 (Medium incl tax)", "electricity", "DC", "I_TAX"),
    ("qep_561.xlsx", "5.6.2 (Medium excl tax)", "electricity", "DC", "X_TAX"),
    ("qep_561.xlsx", "5.6.3 (Large incl tax)", "electricity", "DD", "I_TAX"),
    ("qep_561.xlsx", "5.6.3 (Large excl tax)", "electricity", "DD", "X_TAX"),
    ("qep_5101.xlsx", "5.10.2 (Medium incl tax)", "gas", "D2", "I_TAX"),
    ("qep_5101.xlsx", "5.10.2 (Medium excl tax)", "gas", "D2", "X_TAX"),
]
SOURCE_ID = {"qep_561.xlsx": "desnz_qep_561", "qep_5101.xlsx": "desnz_qep_5101"}


def _rows(path: Path, sheet: str) -> list[tuple]:
    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    if sheet not in wb.sheetnames:
        raise ValueError(f"{path.name}: sheet {sheet!r} not found; sheets are {wb.sheetnames}")
    return list(wb[sheet].iter_rows(values_only=True))


def _number(v) -> float | None:
    if isinstance(v, bool):
        return None
    if isinstance(v, (int, float)):
        return float(v)
    return None  # '..', '' and footnote text are treated as missing


def parse_eu_format(raw: Path = RAW, countries: tuple[str, ...] = ("United Kingdom",)) -> pd.DataFrame:
    """UK (and optionally other countries) semester prices from QEP 5.6.x / 5.10.x.

    Returns tidy rows in GBP per kWh (currency NAC for the UK, matching
    Eurostat's convention) for the 2008-onward methodology only.
    """
    out = []
    for fname, sheet, fuel, band, tax in EU_FORMAT_SHEETS:
        rows = _rows(raw / fname, sheet)
        header_idx = next(i for i, r in enumerate(rows) if r and r[0] == "Year")
        header = [str(c).strip() if c is not None else "" for c in rows[header_idx]]
        for needed in ("Year", "Period", "Methodology", *countries):
            if needed not in header:
                raise ValueError(f"{fname}/{sheet}: column {needed!r} missing")
        col = {name: header.index(name) for name in header if name}
        for r in rows[header_idx + 1:]:
            year = r[col["Year"]]
            if not isinstance(year, (int, float)):
                continue
            method = str(r[col["Methodology"]])
            half = PERIOD_MAP.get(str(r[col["Period"]]).strip())
            if method == "1998-2007" or half is None:
                continue
            period = f"{int(year)}-S{half}"
            if period < "2008-S1":
                continue
            for country in countries:
                pence = _number(r[col[country]])
                out.append({
                    "country": country,
                    "period": period,
                    "fuel": fuel,
                    "band": band,
                    "tax": tax,
                    "price_gbp_per_kwh": None if pence is None else pence / 100,
                    "methodology": method,
                    "source_id": SOURCE_ID[fname],
                    "sheet": sheet,
                })
    df = pd.DataFrame(out)
    dup = df.duplicated(["country", "period", "fuel", "band", "tax"])
    if dup.any():
        raise ValueError(f"DESNZ EU-format tables: duplicate rows {df[dup].head().to_dict('records')}")
    return df


def parse_unit_costs(raw: Path = RAW) -> pd.DataFrame:
    """UK calendar-year unit rate and fixed cost, all payment methods combined."""
    specs = [
        ("qep_224.xlsx", "2.2.4", "electricity", "desnz_qep_224"),
        ("qep_234.xlsx", "2.3.4", "gas", "desnz_qep_234"),
    ]
    out = []
    for fname, sheet, fuel, source_id in specs:
        rows = _rows(raw / fname, sheet)
        header_idx = next(i for i, r in enumerate(rows) if r and r[0] == "Year")
        header = [str(c).strip() if c is not None else "" for c in rows[header_idx]]
        region_col = next(i for i, h in enumerate(header) if h.startswith("Region"))
        unit_col = next(i for i, h in enumerate(header) if h.startswith("Overall: Average variable unit price"))
        fixed_col = next(i for i, h in enumerate(header) if h.startswith("Overall: Average fixed cost"))
        for r in rows[header_idx + 1:]:
            if r[region_col] != "United Kingdom" or r[0] is None:
                continue
            year_txt = str(r[0]).strip()
            year = int(year_txt[:4])
            unit = _number(r[unit_col]) if not isinstance(r[unit_col], str) else float(r[unit_col])
            fixed = _number(r[fixed_col]) if not isinstance(r[fixed_col], str) else float(r[fixed_col])
            out.append({
                "year": year,
                "fuel": fuel,
                "unit_gbp_per_kwh": unit,
                "fixed_gbp_per_year": fixed,
                "provisional": "p" in year_txt[4:],
                "revised": "r" in year_txt[4:],
                "source_id": source_id,
            })
    return pd.DataFrame(out)


def next_update(raw: Path = RAW, fname: str = "qep_561.xlsx") -> str | None:
    """The 'Next update: dd/mm/yyyy' date on a DESNZ table's cover sheet."""
    for r in _rows(raw / fname, "Cover sheet"):
        for c in r:
            if isinstance(c, str) and c.startswith("Next update:"):
                return c.split(":", 1)[1].strip()
    return None

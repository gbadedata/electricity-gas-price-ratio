"""Combine the parsed sources into the published tables."""

from __future__ import annotations

import pandas as pd

from . import assumptions as A
from .geo import name

KEY = ["geo", "period", "fuel", "band", "tax", "currency"]


def clean_eurostat(eurostat: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Apply the documented cleaning rules and log every value they touch.

    1. A price published as exactly 0 is treated as not available. Eurostat
       publishes zeros for Albania and North Macedonia household gas, where
       there is no household gas market to price.
    2. Confidential cells (CONF_STATUS = C) arrive without a value; they stay
       missing and are marked confidential.
    Negative tax-inclusive prices are kept: they are real (a fixed refund
    larger than a very small bill) and are reported by rule W2.
    """
    df = eurostat.copy()
    log = []
    zero = df["price_per_kwh"].eq(0)
    if zero.any():
        z = df[zero]
        log.append(z.assign(action="set to missing", reason="published as exactly 0 (no market priced)"))
        df.loc[zero, "price_per_kwh"] = float("nan")
    conf = df["confidential"] & df["price_per_kwh"].isna()
    if conf.any():
        log.append(df[conf].assign(action="left missing", reason="confidential (CONF_STATUS = C)"))
    log_df = pd.concat(log, ignore_index=True) if log else pd.DataFrame()
    if len(log_df):
        log_df = log_df[KEY + ["action", "reason", "source_id"]]
    return df, log_df


def uk_continuation(eurostat: pd.DataFrame, desnz: pd.DataFrame, fx: pd.DataFrame) -> pd.DataFrame:
    """UK rows from DESNZ for the semesters after Eurostat's last UK observation.

    DESNZ values are GBP per kWh (Eurostat's NAC for the UK). EUR values are
    derived with the ECB semester-average GBP rate, the same convention
    Eurostat uses for national currencies.
    """
    uk_last = eurostat.loc[(eurostat["geo"] == "UK") & eurostat["price_per_kwh"].notna(), "period"].max()
    d = desnz[(desnz["country"] == "United Kingdom") & (desnz["period"] > uk_last)].copy()
    gbp = fx[fx["currency"] == "GBP"].set_index("period")["per_eur"]
    base = pd.DataFrame({
        "geo": "UK",
        "period": d["period"].values,
        "fuel": d["fuel"].values,
        "band": d["band"].values,
        "tax": d["tax"].values,
        "flag": "",
        "confidential": False,
        "source_id": d["source_id"].values,
        "source_last_update": "",
    })
    nac = base.assign(currency="NAC", price_per_kwh=d["price_gbp_per_kwh"].values)
    eur = base.assign(currency="EUR", price_per_kwh=d["price_gbp_per_kwh"].values / d["period"].map(gbp).values)
    return pd.concat([nac, eur], ignore_index=True)


def combine(eurostat: pd.DataFrame, uk_rows: pd.DataFrame) -> pd.DataFrame:
    df = pd.concat([eurostat, uk_rows], ignore_index=True)
    df.insert(1, "country", df["geo"].map(name))
    df = df.sort_values(KEY).reset_index(drop=True)
    return df


def ratios(prices: pd.DataFrame) -> pd.DataFrame:
    """Electricity-to-gas price ratio for each country, semester and tax level.

    Electricity band DC (2,500-4,999 kWh/yr) is the central case; band DD
    (5,000-14,999 kWh/yr), closer to a home that heats with electricity, is
    the sensitivity. Gas is always band D2 (20-199 GJ/yr), the band a typical
    gas-heated home falls in.
    """
    p = prices[prices["price_per_kwh"].notna()]
    gas = p[(p["fuel"] == "gas") & (p["band"] == "D2")]
    elec = p[(p["fuel"] == "electricity") & (p["band"].isin(["DC", "DD"]))]
    on = ["geo", "period", "tax", "currency"]
    m = elec.merge(gas, on=on, suffixes=("_elec", "_gas"))
    out = pd.DataFrame({
        "geo": m["geo"],
        "country": m["country_elec"],
        "period": m["period"],
        "tax": m["tax"],
        "currency": m["currency"],
        "elec_band": m["band_elec"],
        "elec_price_per_kwh": m["price_per_kwh_elec"],
        "gas_price_per_kwh": m["price_per_kwh_gas"],
        "ratio": m["price_per_kwh_elec"] / m["price_per_kwh_gas"],
        "elec_flag": m["flag_elec"],
        "gas_flag": m["flag_gas"],
        "elec_source": m["source_id_elec"],
        "gas_source": m["source_id_gas"],
    })
    out["hp_to_boiler_running_cost"] = out["ratio"] * A.BOILER_EFF_CENTRAL / A.SPF_CENTRAL
    out["hp_cheaper_central"] = out["ratio"] < A.BREAKEVEN_CENTRAL
    out["hp_verdict"] = pd.cut(
        out["ratio"],
        bins=[0, A.BREAKEVEN_LOW, A.BREAKEVEN_HIGH, float("inf")],
        labels=["cheaper", "depends on install", "dearer"],
        right=False,
    ).astype(str)
    return out.sort_values(["geo", "period", "tax", "currency", "elec_band"]).reset_index(drop=True)


def gb_annual_crosscheck(desnz_eu: pd.DataFrame, unit_costs: pd.DataFrame,
                         elec_kwh: float = 3750, gas_kwh: float = 12000) -> pd.DataFrame:
    """Compare two DESNZ series for the UK on a calendar-year basis.

    The EU-format series (QEP 5.6.2 / 5.10.2, tax included) is averaged over
    the two semesters of a year, unweighted, as DESNZ does in its annual
    tables. The bills series (QEP 2.2.4 / 2.3.4) gives a unit rate and an
    annual fixed cost; spreading the fixed cost over a representative
    consumption in the same band gives a comparable average price.
    """
    eu = desnz_eu[(desnz_eu["country"] == "United Kingdom") & (desnz_eu["tax"] == "I_TAX")
                  & (desnz_eu["band"].isin(["DC", "D2"]))].copy()
    eu["year"] = eu["period"].str[:4].astype(int)
    sem = eu.groupby(["year", "fuel"]).agg(
        semester_mean=("price_gbp_per_kwh", "mean"),
        n_semesters=("price_gbp_per_kwh", "count"),
        s1=("price_gbp_per_kwh", "first"),
        s2=("price_gbp_per_kwh", "last"),
    ).reset_index()
    sem = sem[sem["n_semesters"] == 2]
    u = unit_costs.copy()
    kwh = u["fuel"].map({"electricity": elec_kwh, "gas": gas_kwh})
    u["bills_avg_price"] = u["unit_gbp_per_kwh"] + u["fixed_gbp_per_year"] / kwh
    u["bills_avg_price_low_use"] = u["unit_gbp_per_kwh"] + u["fixed_gbp_per_year"] / (kwh * 2 / 3)
    u["bills_avg_price_high_use"] = u["unit_gbp_per_kwh"] + u["fixed_gbp_per_year"] / (kwh * 4 / 3)
    j = sem.merge(u, on=["year", "fuel"])
    j["gap_pct"] = (j["semester_mean"] / j["bills_avg_price"] - 1) * 100
    j["gap_pct_range"] = [
        f"{(r.semester_mean / r.bills_avg_price_low_use - 1) * 100:+.1f} to {(r.semester_mean / r.bills_avg_price_high_use - 1) * 100:+.1f}"
        for r in j.itertuples()
    ]
    return j.sort_values(["fuel", "year"]).reset_index(drop=True)


def gb_ratio_methods(desnz_eu: pd.DataFrame, unit_costs: pd.DataFrame) -> pd.DataFrame:
    """UK ratio three ways for each year: average price (semester series),
    average price (bills series) and unit rate only (what a household switching
    from gas to a heat pump actually saves per kWh)."""
    cc = gb_annual_crosscheck(desnz_eu, unit_costs)
    e = cc[cc["fuel"] == "electricity"].set_index("year")
    g = cc[cc["fuel"] == "gas"].set_index("year")
    years = e.index.intersection(g.index)
    out = pd.DataFrame({
        "year": years,
        "ratio_semester_avg_price": (e.loc[years, "semester_mean"] / g.loc[years, "semester_mean"]).values,
        "ratio_bills_avg_price": (e.loc[years, "bills_avg_price"] / g.loc[years, "bills_avg_price"]).values,
        "ratio_unit_rate": (e.loc[years, "unit_gbp_per_kwh"] / g.loc[years, "unit_gbp_per_kwh"]).values,
    })
    return out

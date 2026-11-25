"""Quality rules run on every build.

Blocking rules stop the build: nothing is published if one fails. Warning
rules never stop it; they record what a user of the data needs to know,
with the rows that triggered them, in reports/validation_report.md.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd

from .geo import AGGREGATES, EU27
from .transform import KEY

BAND_ORDER = {"electricity": ["DA", "DB", "DC", "DD", "DE"], "gas": ["D1", "D2", "D3"]}


@dataclass
class Check:
    id: str
    title: str
    severity: str  # "blocking" or "warning"
    checked: int
    failed: int
    detail: str
    examples: list[dict] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return self.failed == 0


def _examples(df: pd.DataFrame, cols: list[str], n: int = 12) -> list[dict]:
    return df[cols].head(n).round(4).to_dict("records")


def schema_and_keys(prices: pd.DataFrame) -> Check:
    dup = prices.duplicated(KEY, keep=False)
    bad_period = ~prices["period"].str.match(r"^\d{4}-S[12]$")
    bad_tax = ~prices["tax"].isin(["X_TAX", "X_VAT", "I_TAX"])
    bad_cur = ~prices["currency"].isin(["EUR", "NAC"])
    bad = prices[dup | bad_period | bad_tax | bad_cur]
    return Check("B1", "One row per country, semester, fuel, band, tax level and currency; valid codes",
                 "blocking", len(prices), len(bad), "Duplicate keys or unknown period, tax or currency codes.",
                 _examples(bad, KEY))


def plausible_values(prices: pd.DataFrame) -> Check:
    v = prices[prices["price_per_kwh"].notna() & (prices["currency"] == "EUR")]
    ratio_band = v["band"].isin(["DC", "DD", "D2"])
    pre_tax = v["tax"] == "X_TAX"
    out_of_range = (v["price_per_kwh"] <= 0) | (v["price_per_kwh"] > 2)
    bad = v[out_of_range & (ratio_band | pre_tax)]
    return Check("B2", "Prices used in the ratio, and every pre-tax price, are above zero and below EUR 2/kWh",
                 "blocking", int((ratio_band | pre_tax).sum()), len(bad),
                 "Outside this range points to a unit or parsing error. Tax-inclusive prices in the two smallest "
                 "electricity bands are exempt: they can be negative when a fixed annual refund exceeds a very "
                 "small bill (see W2).",
                 _examples(bad, KEY + ["price_per_kwh"]))


def uk_splice_overlap(eurostat: pd.DataFrame, desnz: pd.DataFrame, tol_pct: float = 1.0) -> tuple[Check, pd.DataFrame]:
    e = eurostat[(eurostat["geo"] == "UK") & (eurostat["currency"] == "NAC")]
    d = desnz[desnz["country"] == "United Kingdom"]
    j = e.merge(d, on=["period", "fuel", "band", "tax"], how="inner")
    j = j[j["price_per_kwh"].notna() & j["price_gbp_per_kwh"].notna()].copy()
    j["diff_pct"] = (j["price_gbp_per_kwh"] / j["price_per_kwh"] - 1) * 100
    bad = j[j["diff_pct"].abs() > tol_pct]
    detail = (f"Before joining the DESNZ UK series onto Eurostat's, both must agree where they overlap. "
              f"{len(j)} overlapping values ({j['period'].min()} to {j['period'].max()}); "
              f"largest difference {j['diff_pct'].abs().max():.2f}%. Tolerance {tol_pct}%.")
    return (Check("B3", "DESNZ and Eurostat agree on UK prices where both publish", "blocking", len(j), len(bad), detail,
                  _examples(bad, ["period", "fuel", "band", "tax", "price_per_kwh", "price_gbp_per_kwh", "diff_pct"])),
            j)


def currency_invariance(ratio: pd.DataFrame, tol_pct: float = 0.5) -> Check:
    r = ratio[~ratio["geo"].isin(AGGREGATES)]
    e = r[r["currency"] == "EUR"]
    n = r[r["currency"] == "NAC"]
    j = e.merge(n, on=["geo", "period", "tax", "elec_band"], suffixes=("_eur", "_nac"))
    j["diff_pct"] = (j["ratio_eur"] / j["ratio_nac"] - 1) * 100
    bad = j[j["diff_pct"].abs() > tol_pct]
    return Check("W1", "The ratio is the same whether computed in euro or in national currency", "warning",
                 len(j), len(bad),
                 "A unit-free ratio should not depend on currency; differences beyond rounding of the published "
                 "4-decimal prices would mean the two fuels were converted at different rates.",
                 _examples(bad, ["geo", "period", "tax", "elec_band", "ratio_eur", "ratio_nac", "diff_pct"]))


def tax_ordering(prices: pd.DataFrame) -> Check:
    p = prices[(prices["currency"] == "EUR") & prices["price_per_kwh"].notna()
               & prices["band"].isin(["DC", "DD", "D2"]) & ~prices["geo"].isin(AGGREGATES)]
    w = p.pivot_table(index=["geo", "period", "fuel", "band"], columns="tax", values="price_per_kwh").dropna()
    bad = w[w["I_TAX"] < w["X_TAX"]].reset_index()
    bad["net_taxes_per_kwh"] = bad["I_TAX"] - bad["X_TAX"]
    bad = bad.sort_values(["period", "geo"])
    by_geo = bad.groupby("geo")["period"].agg(["min", "max", "count"])
    summary = "; ".join(f"{g} {r['min']}-{r['max']} ({r['count']})" for g, r in by_geo.iterrows())
    return Check("W2", "Tax-inclusive price is at least the tax-exclusive price (bands used in the ratio)",
                 "warning", len(w), len(bad),
                 "Eurostat includes subsidies and allowances in the tax component from 2021, so where government "
                 "support exceeded taxes and levies the 'all taxes included' price falls below the price before "
                 "taxes. The Netherlands' fixed annual energy-tax refund has the same effect (DESNZ notes it). "
                 "For these rows the tax-inclusive ratio measures support policy as much as tax policy. "
                 f"By country, first-last semester (count): {summary}.",
                 _examples(bad, ["geo", "period", "fuel", "band", "X_TAX", "I_TAX", "net_taxes_per_kwh"]))


def band_ordering(prices: pd.DataFrame) -> Check:
    p = prices[(prices["currency"] == "EUR") & (prices["tax"] == "I_TAX") & prices["price_per_kwh"].notna()
               & ~prices["geo"].isin(AGGREGATES)]
    rows, checked = [], 0
    for fuel, order in BAND_ORDER.items():
        w = p[p["fuel"] == fuel].pivot_table(index=["geo", "period"], columns="band", values="price_per_kwh")
        for a, b in zip(order, order[1:]):
            if a in w and b in w:
                pair = w[[a, b]].dropna()
                checked += len(pair)
                hit = pair[pair[b] > pair[a] * 1.05].reset_index()
                for r in hit.itertuples(index=False):
                    rows.append({"geo": r.geo, "period": r.period, "fuel": fuel, "lower_band": a,
                                 "higher_band": b, "lower_price": getattr(r, a), "higher_price": getattr(r, b)})
    bad = pd.DataFrame(rows)
    top = ""
    if len(bad):
        c = bad.groupby("geo").size().sort_values(ascending=False)
        top = " Most frequent: " + ", ".join(f"{g} ({n})" for g, n in c.head(8).items()) + "."
        bad = bad.sort_values(["geo", "period"])
    return Check("W3", "Larger consumers do not pay more than 5% above smaller ones (tax included)", "warning",
                 checked, len(bad),
                 "Fixed charges spread over more kWh normally make the average price fall with consumption. "
                 "Exceptions come from rising-block tariffs, refunds that make the smallest bands negative, or "
                 "support capped at a volume, so they are reported rather than corrected." + top,
                 bad.head(12).round(4).to_dict("records") if len(bad) else [])


def fx_consistency(prices: pd.DataFrame, fx: pd.DataFrame, tol_pct: float = 2.0) -> tuple[Check, pd.DataFrame]:
    p = prices[prices["price_per_kwh"].notna() & (prices["source_id"].str.startswith("eurostat"))]
    w = p.pivot_table(index=["geo", "period", "fuel", "band", "tax"], columns="currency", values="price_per_kwh").dropna()
    w = w[(w["EUR"] > 0)]
    w["implied_per_eur"] = w["NAC"] / w["EUR"]
    w = w.reset_index()
    # Euro-area members report NAC == EUR; keep only countries with their own currency at that time.
    w = w[(w["implied_per_eur"] - 1).abs() > 1e-6]
    cur = {"BG": "BGN", "CZ": "CZK", "DK": "DKK", "HU": "HUF", "PL": "PLN", "RO": "RON", "SE": "SEK",
           "UK": "GBP", "NO": "NOK", "IS": "ISK", "TR": "TRY", "HR": "HRK", "LI": "CHF"}
    w["currency"] = w["geo"].map(cur)
    w = w.dropna(subset=["currency"]).merge(fx, on=["currency", "period"], how="inner")
    w["diff_pct"] = (w["implied_per_eur"] / w["per_eur"] - 1) * 100
    g = w.groupby(["geo", "period"]).agg(implied=("implied_per_eur", "median"), ecb=("per_eur", "first"),
                                         diff_pct=("diff_pct", "median")).reset_index()
    bad = g[g["diff_pct"].abs() > tol_pct].sort_values("diff_pct", key=abs, ascending=False)
    return (Check("W4", "Eurostat's euro prices match its national-currency prices at the ECB semester-average rate",
                  "warning", len(g), len(bad),
                  f"Implied rate = national-currency price / euro price, compared with the mean of the ECB's six "
                  f"monthly averages. Tolerance {tol_pct}%.",
                  _examples(bad, ["geo", "period", "implied", "ecb", "diff_pct"])),
            g)


def flagged_inputs(ratio: pd.DataFrame) -> Check:
    r = ratio[(ratio["currency"] == "EUR") & (ratio["tax"] == "I_TAX") & (ratio["elec_band"] == "DC")]
    hit = r[(r["elec_flag"] != "") | (r["gas_flag"] != "")]
    counts = pd.concat([hit["elec_flag"], hit["gas_flag"]]).replace("", pd.NA).dropna().value_counts().to_dict()
    return Check("W5", "Ratios built on flagged Eurostat values", "warning", len(r), len(hit),
                 "Flags: e = estimated, p = provisional, d = definition differs, b = break in series. "
                 f"Counts across both fuels: {counts}. Flagged values are kept and the flag carried into the "
                 "ratio table, so users can exclude them.",
                 _examples(hit, ["geo", "period", "ratio", "elec_flag", "gas_flag"]))


def big_moves(prices: pd.DataFrame, threshold: float = 0.5) -> Check:
    p = prices[(prices["currency"] == "EUR") & (prices["tax"] == "I_TAX") & prices["price_per_kwh"].notna()
               & prices["band"].isin(["DC", "D2"])].sort_values(["geo", "fuel", "band", "period"])
    p = p.copy()
    p["prev"] = p.groupby(["geo", "fuel", "band"])["price_per_kwh"].shift()
    p["change"] = p["price_per_kwh"] / p["prev"] - 1
    v = p.dropna(subset=["change"])
    bad = v[v["change"].abs() > threshold].sort_values("change", key=abs, ascending=False)
    return Check("W6", f"Semester-on-semester price moves above {threshold:.0%}", "warning", len(v), len(bad),
                 "Not errors in themselves (2022 was extraordinary) but each one was looked at before publication.",
                 _examples(bad, ["geo", "period", "fuel", "prev", "price_per_kwh", "change"]))


def gb_crosscheck(cc: pd.DataFrame, tol_pct: float = 10.0) -> Check:
    bad = cc[cc["gap_pct"].abs() > tol_pct]
    return Check("W7", "UK semester prices agree with DESNZ's separate bills series", "warning", len(cc), len(bad),
                 "Annual mean of the two semester prices (tax included) against unit rate plus fixed cost spread "
                 f"over 3,750 kWh (electricity) or 12,000 kWh (gas). Tolerance {tol_pct}%. The two series differ in "
                 "scope (all tariffs in a consumption band against standard tariffs only) and weighting, so small "
                 "gaps are expected; large ones point to a difference in how support was recorded.",
                 _examples(bad, ["year", "fuel", "s1", "s2", "semester_mean", "unit_gbp_per_kwh",
                                 "fixed_gbp_per_year", "bills_avg_price", "gap_pct", "gap_pct_range"]))


def coverage(ratio: pd.DataFrame, prices: pd.DataFrame) -> Check:
    r = ratio[(ratio["currency"] == "EUR") & (ratio["tax"] == "I_TAX") & (ratio["elec_band"] == "DC")]
    latest = r["period"].max()
    have = set(r.loc[r["period"] == latest, "geo"])
    missing = sorted(EU27 - have)
    reasons = []
    for g in missing:
        has_e = ((prices["geo"] == g) & (prices["fuel"] == "electricity") & (prices["period"] == latest)
                 & prices["price_per_kwh"].notna()).any()
        has_g = ((prices["geo"] == g) & (prices["fuel"] == "gas") & prices["price_per_kwh"].notna()).any()
        d2 = (prices["geo"] == g) & (prices["fuel"] == "gas") & (prices["band"] == "D2") & prices["confidential"]
        conf = (d2 & (prices["period"] == latest)).any()
        if not has_g:
            why = "no household gas price ever published"
        elif conf:
            first = prices.loc[d2, "period"].min()
            why = f"gas price confidential since {first}"
        else:
            why = "no gas price for this semester" if has_e else "no electricity price for this semester"
        reasons.append({"geo": g, "reason": why})
    return Check("W8", f"EU countries with a ratio in the latest semester ({latest})", "warning", 27, len(missing),
                 f"{27 - len(missing)} of 27 EU countries have both prices in {latest}.", reasons)


def run_all(eurostat, desnz_eu, prices, ratio, fx, cc) -> tuple[list[Check], dict]:
    b3, overlap = uk_splice_overlap(eurostat, desnz_eu)
    w4, fx_table = fx_consistency(prices, fx)
    checks = [
        schema_and_keys(prices),
        plausible_values(prices),
        b3,
        currency_invariance(ratio),
        tax_ordering(prices),
        band_ordering(prices),
        w4,
        flagged_inputs(ratio),
        big_moves(prices),
        gb_crosscheck(cc),
        coverage(ratio, prices),
    ]
    return checks, {"uk_overlap": overlap, "fx": fx_table}

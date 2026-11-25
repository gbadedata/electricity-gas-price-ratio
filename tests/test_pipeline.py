"""Tests run against the committed raw snapshot, plus planted defects that each rule must catch."""

from __future__ import annotations

import json
import shutil

import numpy as np
import pandas as pd
import pytest

from epr import assumptions as A
from epr import fetch, parse_desnz, parse_ecb, parse_eurostat, transform, validate
from epr.paths import MANIFEST, RAW


@pytest.fixture(scope="module")
def data():
    eurostat, components = parse_eurostat.load_all()
    eurostat, log = transform.clean_eurostat(eurostat)
    desnz = parse_desnz.parse_eu_format()
    units = parse_desnz.parse_unit_costs()
    fx = parse_ecb.semester_average(parse_ecb.parse_monthly())
    prices = transform.combine(eurostat, transform.uk_continuation(eurostat, desnz, fx))
    ratio = transform.ratios(prices)
    return dict(eurostat=eurostat, log=log, desnz=desnz, units=units, fx=fx, prices=prices, ratio=ratio)


def _price(df, geo, period, fuel, band, tax, currency="EUR"):
    r = df[(df.geo == geo) & (df.period == period) & (df.fuel == fuel) & (df.band == band)
           & (df.tax == tax) & (df.currency == currency)]
    assert len(r) == 1
    return r["price_per_kwh"].iloc[0]


# --- the snapshot itself ---------------------------------------------------

def test_manifest_matches_raw_files():
    assert fetch.verify_manifest() == []


def test_manifest_detects_a_changed_byte(tmp_path):
    raw = tmp_path / "raw"
    shutil.copytree(RAW, raw)
    target = raw / "nrg_pc_202.csv"
    body = bytearray(target.read_bytes())
    body[-5] = ord("9") if body[-5] != ord("9") else ord("8")
    target.write_bytes(bytes(body))
    problems = fetch.verify_manifest(raw, raw / "manifest.json")
    assert any("eurostat_nrg_pc_202" in p for p in problems)


# --- parsing ---------------------------------------------------------------

def test_eurostat_values_match_published_figures(data):
    # Checked by hand against the Eurostat API on 25 Nov 2026.
    assert _price(data["eurostat"], "UK", "2019-S2", "electricity", "DC", "I_TAX") == pytest.approx(0.221)
    assert _price(data["eurostat"], "DE", "2025-S1", "gas", "D2", "I_TAX") == pytest.approx(0.1216)


def test_eurostat_keeps_only_post_2007_bands(data):
    assert set(data["eurostat"]["band"]) <= {"DA", "DB", "DC", "DD", "DE", "D1", "D2", "D3", "ALL"}
    assert data["eurostat"]["period"].min() >= "2007-S2"


def test_desnz_uk_series_runs_past_eurostat(data):
    uk = data["desnz"][(data["desnz"].country == "United Kingdom") & (data["desnz"].band == "DC")
                       & (data["desnz"].tax == "I_TAX")]
    assert uk["period"].min() == "2008-S1"
    assert uk["period"].max() >= "2025-S2"
    assert uk["price_gbp_per_kwh"].between(0.05, 1).all()


def test_ecb_semester_average_needs_six_months():
    monthly = pd.DataFrame({"currency": ["GBP"] * 7, "month": [f"2025-0{m}" for m in range(1, 8)],
                            "per_eur": [0.8, 0.8, 0.8, 0.8, 0.8, 0.86, 0.9]})
    s = parse_ecb.semester_average(monthly)
    assert list(s["period"]) == ["2025-S1"]
    assert s["per_eur"].iloc[0] == pytest.approx(0.81)


# --- cleaning and combining ------------------------------------------------

def test_zero_prices_become_missing_and_are_logged(data):
    assert not (data["eurostat"]["price_per_kwh"] == 0).any()
    zeros = data["log"][data["log"].reason.str.contains("exactly 0")]
    assert set(zeros["geo"]) == {"AL", "MK"}


def test_uk_euro_values_use_the_ecb_semester_rate(data):
    p = data["prices"]
    gbp = _price(p, "UK", "2025-S2", "electricity", "DC", "I_TAX", "NAC")
    eur = _price(p, "UK", "2025-S2", "electricity", "DC", "I_TAX", "EUR")
    rate = data["fx"].query("currency == 'GBP' and period == '2025-S2'")["per_eur"].iloc[0]
    assert eur == pytest.approx(gbp / rate)


def test_ratio_and_break_even_arithmetic(data):
    r = data["ratio"]
    assert np.allclose(r["ratio"], r["elec_price_per_kwh"] / r["gas_price_per_kwh"])
    at_breakeven = A.BREAKEVEN_CENTRAL * A.BOILER_EFF_CENTRAL / A.SPF_CENTRAL
    assert at_breakeven == pytest.approx(1.0)
    assert (r["hp_cheaper_central"] == (r["ratio"] < A.BREAKEVEN_CENTRAL)).all()


def test_ratio_has_no_infinite_or_missing_values(data):
    assert np.isfinite(data["ratio"]["ratio"]).all()


# --- every blocking rule passes on the real data ...

def test_blocking_rules_pass(data):
    cc = transform.gb_annual_crosscheck(data["desnz"], data["units"])
    checks, _ = validate.run_all(data["eurostat"], data["desnz"], data["prices"], data["ratio"], data["fx"], cc)
    failed = [c.id for c in checks if c.severity == "blocking" and not c.passed]
    assert failed == []


# --- ... and catches defects planted into it -------------------------------

def test_b1_catches_a_duplicated_row(data):
    bad = pd.concat([data["prices"], data["prices"].iloc[[100]]])
    assert not validate.schema_and_keys(bad).passed


def test_b2_catches_a_price_in_cents_not_euro(data):
    bad = data["prices"].copy()
    i = bad.index[(bad.geo == "FR") & (bad.band == "DC") & (bad.currency == "EUR")][0]
    bad.loc[i, "price_per_kwh"] *= 100
    assert not validate.plausible_values(bad).passed


def test_b2_allows_real_negative_prices_in_the_smallest_band(data):
    p = data["prices"]
    assert (p[(p.geo == "NL") & (p.band == "DA") & (p.tax == "I_TAX")]["price_per_kwh"] < 0).any()
    assert validate.plausible_values(p).passed


def test_b3_catches_a_bad_splice(data):
    bad = data["desnz"].copy()
    bad.loc[bad.country == "United Kingdom", "price_gbp_per_kwh"] *= 1.05
    check, _ = validate.uk_splice_overlap(data["eurostat"], bad)
    assert not check.passed


def test_w4_catches_a_wrong_exchange_rate(data):
    bad = data["prices"].copy()
    m = (bad.geo == "SE") & (bad.period == "2025-S1") & (bad.currency == "EUR")
    bad.loc[m, "price_per_kwh"] *= 1.10
    check, _ = validate.fx_consistency(bad, data["fx"])
    assert any(e["geo"] == "SE" and e["period"] == "2025-S1" for e in check.examples)


def test_manifest_fixture_is_current():
    m = json.loads(MANIFEST.read_text())
    assert {s["id"] for s in m["sources"]} >= {"eurostat_nrg_pc_204", "eurostat_nrg_pc_202", "desnz_qep_561",
                                               "desnz_qep_5101", "ecb_exr_monthly"}

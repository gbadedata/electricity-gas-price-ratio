"""Build the published dataset from the raw snapshot: parse, combine, validate, write."""

from __future__ import annotations

import json
import sys
import pandas as pd

from . import assumptions as A
from . import parse_desnz, parse_ecb, parse_eurostat, transform, validate
from .paths import MANIFEST, PROCESSED, REPORTS


def _write_csv(df: pd.DataFrame, name: str, float_format: str = "%.6g") -> None:
    PROCESSED.mkdir(parents=True, exist_ok=True)
    df.to_csv(PROCESSED / name, index=False, float_format=float_format, lineterminator="\n")


def _report_md(checks: list[validate.Check], manifest: dict) -> str:
    lines = [
        "# Validation report",
        "",
        f"Raw snapshot fetched {manifest['fetched_at']}. Every rule below runs on every build; "
        "a failed blocking rule stops the build before anything is written.",
        "",
        "| Rule | Check | Severity | Checked | Flagged | Result |",
        "|---|---|---|---:|---:|---|",
    ]
    for c in checks:
        result = "pass" if c.passed else ("FAIL" if c.severity == "blocking" else "see below")
        lines.append(f"| {c.id} | {c.title} | {c.severity} | {c.checked:,} | {c.failed:,} | {result} |")
    for c in checks:
        lines += ["", f"## {c.id}. {c.title}", "", c.detail]
        if c.examples:
            ex = pd.DataFrame(c.examples)
            lines += ["", f"First {len(ex)} of {c.failed:,}:" if c.failed > len(ex) else "Rows:", "",
                      ex.to_markdown(index=False)]
    return "\n".join(lines) + "\n"


def build() -> int:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))

    eurostat, components = parse_eurostat.load_all()
    eurostat, cleaning_log = transform.clean_eurostat(eurostat)
    desnz_eu = parse_desnz.parse_eu_format()
    unit_costs = parse_desnz.parse_unit_costs()
    fx = parse_ecb.semester_average(parse_ecb.parse_monthly())

    uk_rows = transform.uk_continuation(eurostat, desnz_eu, fx)
    prices = transform.combine(eurostat, uk_rows)
    ratio = transform.ratios(prices)
    cc = transform.gb_annual_crosscheck(desnz_eu, unit_costs)
    gb_methods = transform.gb_ratio_methods(desnz_eu, unit_costs)

    checks, extras = validate.run_all(eurostat, desnz_eu, prices, ratio, fx, cc)
    REPORTS.mkdir(parents=True, exist_ok=True)
    (REPORTS / "validation_report.md").write_text(_report_md(checks, manifest), encoding="utf-8")
    (REPORTS / "validation_summary.json").write_text(json.dumps({
        "raw_fetched_at": manifest["fetched_at"],
        "checks": [{"id": c.id, "title": c.title, "severity": c.severity, "checked": c.checked,
                    "flagged": c.failed, "passed": c.passed} for c in checks],
    }, indent=2) + "\n", encoding="utf-8")

    blocking = [c for c in checks if c.severity == "blocking" and not c.passed]
    for c in checks:
        status = "ok" if c.passed else ("FAILED" if c.severity == "blocking" else "warn")
        print(f"[{status:>6}] {c.id} {c.title}: {c.failed}/{c.checked}", file=sys.stderr)
    if blocking:
        print("Blocking checks failed; processed data not updated.", file=sys.stderr)
        return 1

    _write_csv(prices, "household_prices.csv")
    _write_csv(ratio, "electricity_gas_ratio.csv")
    _write_csv(components, "price_components.csv")
    _write_csv(cc, "uk_series_crosscheck.csv")
    _write_csv(gb_methods, "uk_ratio_methods.csv")
    _write_csv(extras["uk_overlap"][["period", "fuel", "band", "tax", "price_per_kwh", "price_gbp_per_kwh", "diff_pct"]]
               .rename(columns={"price_per_kwh": "eurostat_gbp_per_kwh", "price_gbp_per_kwh": "desnz_gbp_per_kwh"}),
               "uk_splice_overlap.csv")
    _write_csv(extras["fx"], "fx_check.csv")
    _write_csv(cleaning_log, "cleaning_log.csv")
    (PROCESSED / "build_info.json").write_text(json.dumps({
        "raw_fetched_at": manifest["fetched_at"],
        "raw_sha256": {s["id"]: s["sha256"] for s in manifest["sources"]},
        "assumptions": {
            "spf_central": A.SPF_CENTRAL, "spf_range": [A.SPF_LOW, A.SPF_HIGH],
            "boiler_efficiency_central_gcv": A.BOILER_EFF_CENTRAL,
            "boiler_efficiency_range_gcv": [A.BOILER_EFF_LOW, A.BOILER_EFF_HIGH],
            "breakeven_ratio_central": round(A.BREAKEVEN_CENTRAL, 4),
            "breakeven_ratio_range": [round(A.BREAKEVEN_LOW, 4), round(A.BREAKEVEN_HIGH, 4)],
            "sources": A.SOURCES,
        },
        "rows": {"household_prices": len(prices), "electricity_gas_ratio": len(ratio)},
    }, indent=2) + "\n", encoding="utf-8")

    from .analyse import analyse
    analyse(prices, ratio, cc, gb_methods, checks)
    return 0

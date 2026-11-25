"""Findings and charts, computed from the published tables on every build.

Nothing in reports/findings.md is typed by hand: each number is read from
the processed data, so a refresh that changes the data changes the text.
"""

from __future__ import annotations

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402
import textwrap  # noqa: E402

from . import assumptions as A  # noqa: E402
from .geo import EU27, name  # noqa: E402
from .parse_desnz import next_update  # noqa: E402
from .paths import FIGURES, REPORTS  # noqa: E402

# Reference palette (light mode) from the dataviz guidance.
BLUE, ORANGE, AQUA, YELLOW = "#2a78d6", "#eb6834", "#1baf7a", "#eda100"
INK, INK2, SURFACE, GRID, BAND = "#0b0b0b", "#52514e", "#fcfcfb", "#e4e3df", "#efeeea"

plt.rcParams.update({
    "font.family": "DejaVu Sans", "font.size": 10, "axes.edgecolor": GRID, "axes.labelcolor": INK2,
    "xtick.color": INK2, "ytick.color": INK2, "axes.titlesize": 12, "axes.titleweight": "bold",
    "axes.titlecolor": INK, "figure.facecolor": SURFACE, "axes.facecolor": SURFACE,
    "axes.spines.top": False, "axes.spines.right": False, "savefig.dpi": 160,
})


def _central(ratio: pd.DataFrame, tax: str = "I_TAX", band: str = "DC") -> pd.DataFrame:
    return ratio[(ratio["currency"] == "EUR") & (ratio["tax"] == tax) & (ratio["elec_band"] == band)]


def latest_by_country(ratio: pd.DataFrame, tax: str = "I_TAX", band: str = "DC") -> pd.DataFrame:
    """EU members in the latest EU semester, plus the UK at its latest semester."""
    c = _central(ratio, tax, band)
    eu_latest = c.loc[c["geo"] == "EU27_2020", "period"].max()
    eu = c[(c["period"] == eu_latest) & c["geo"].isin(EU27)]
    uk = c[c["geo"] == "UK"]
    uk = uk[uk["period"] == uk["period"].max()]
    return pd.concat([eu, uk]).sort_values("ratio").reset_index(drop=True), eu_latest


def _note(fig, text: str, width: int) -> None:
    wrapped = "\n".join(textwrap.fill(part, width) for part in text.split("\n"))
    fig.text(0.01, 0.01, wrapped, fontsize=7.5, color=INK2, va="bottom")


def _breakeven_band(ax, vertical: bool) -> None:
    span = ax.axvspan if vertical else ax.axhspan
    line = ax.axvline if vertical else ax.axhline
    span(A.BREAKEVEN_LOW, A.BREAKEVEN_HIGH, color=BAND, zorder=0, lw=0)
    line(A.BREAKEVEN_CENTRAL, color=INK2, lw=1, ls=(0, (4, 3)), zorder=1)


def fig_latest(latest: pd.DataFrame, eu_latest: str) -> str:
    fig, ax = plt.subplots(figsize=(8, 7.2))
    _breakeven_band(ax, vertical=True)
    y = range(len(latest))
    colours = [ORANGE if g == "UK" else BLUE for g in latest["geo"]]
    ax.barh(list(y), latest["ratio"], color=colours, height=0.62, zorder=2)
    labels = [f"{name(g)}" + (f" ({p})" if g == "UK" else "") for g, p in zip(latest["geo"], latest["period"])]
    ax.set_yticks(list(y), labels)
    for i, v in enumerate(latest["ratio"]):
        ax.text(v + 0.04, i, f"{v:.2f}", va="center", fontsize=8.5, color=INK2)
    ax.text(A.BREAKEVEN_CENTRAL + 0.05, -1.05, f"central break-even {A.BREAKEVEN_CENTRAL:.1f}", fontsize=8, color=INK2)
    ax.text(A.BREAKEVEN_LOW + 0.05, -1.75, "shaded: depends on the installation", fontsize=8, color=INK2)
    ax.set_ylim(-2.1, len(latest) - 0.4)
    ax.set_xlabel("Household electricity price ÷ gas price (all taxes and levies included)")
    ax.set_title(f"Electricity-to-gas price ratio, {eu_latest} (UK: latest available)", loc="left")
    ax.grid(axis="x", color=GRID, lw=0.8, zorder=0)
    ax.tick_params(axis="y", length=0)
    _note(fig, "Electricity band DC (2,500-4,999 kWh/yr), gas band D2 (20-199 GJ/yr), average prices. Left of the dashed "
          f"line a heat pump (SPF {A.SPF_CENTRAL}) is cheaper to run than a gas boiler ({A.BOILER_EFF_CENTRAL:.0%} efficient).\n"
          "Sources: Eurostat nrg_pc_204 and nrg_pc_202; DESNZ QEP 5.6.2 and 5.10.2 (UK).", 120)
    fig.tight_layout(rect=(0, 0.06, 1, 1))
    path = FIGURES / "ratio_by_country_latest.png"
    fig.savefig(path)
    plt.close(fig)
    return path.name


def fig_over_time(ratio: pd.DataFrame) -> str:
    c = _central(ratio)
    series = [("EU27_2020", "EU27", BLUE), ("UK", "United Kingdom", ORANGE), ("DE", "Germany", AQUA), ("FR", "France", YELLOW)]
    fig, ax = plt.subplots(figsize=(9, 4.8))
    _breakeven_band(ax, vertical=False)
    periods = sorted(c["period"].unique())
    x_of = {p: i for i, p in enumerate(periods)}
    for geo, label, colour in series:
        s = c[c["geo"] == geo].sort_values("period")
        x = [x_of[p] for p in s["period"]]
        ax.plot(x, s["ratio"], color=colour, lw=2, label=label, zorder=3)
        ax.text(x[-1] + 0.4, s["ratio"].iloc[-1], label, color=INK, fontsize=9, va="center")
    ticks = [i for i, p in enumerate(periods) if p.endswith("S1") and int(p[:4]) % 2 == 0]
    ax.set_xticks(ticks, [periods[i][:4] for i in ticks])
    ax.set_xlim(-0.5, len(periods) + 5)
    ax.set_ylabel("Electricity price ÷ gas price")
    ax.set_title("Electricity-to-gas price ratio, households, 2007-2026", loc="left")
    ax.grid(axis="y", color=GRID, lw=0.8, zorder=0)
    ax.legend(frameon=False, loc="upper left", ncol=4, fontsize=9)
    _note(fig, "Half-yearly, all taxes and levies included; electricity band DC, gas band D2. Shaded: break-even range "
          f"{A.BREAKEVEN_LOW:.1f}-{A.BREAKEVEN_HIGH:.1f}; dashed: central break-even {A.BREAKEVEN_CENTRAL:.1f}. "
          "UK after 2020-S1 from DESNZ, which collects it with Eurostat's method.", 135)
    fig.tight_layout(rect=(0, 0.06, 1, 1))
    path = FIGURES / "ratio_over_time.png"
    fig.savefig(path)
    plt.close(fig)
    return path.name


def tax_effect(ratio: pd.DataFrame) -> pd.DataFrame:
    inc, _ = latest_by_country(ratio, "I_TAX")
    exc = _central(ratio, "X_TAX")
    t = inc.merge(exc[["geo", "period", "ratio"]], on=["geo", "period"], suffixes=("_incl", "_excl"))
    t["tax_effect_pct"] = (t["ratio_incl"] / t["ratio_excl"] - 1) * 100
    return t.sort_values("tax_effect_pct").reset_index(drop=True)


def fig_tax(t: pd.DataFrame) -> str:
    fig, ax = plt.subplots(figsize=(8, 7.2))
    y = list(range(len(t)))
    for i, r in t.iterrows():
        ax.plot([r["ratio_excl"], r["ratio_incl"]], [i, i], color=GRID, lw=2.5, zorder=1, solid_capstyle="round")
    ax.scatter(t["ratio_excl"], y, s=42, color=BLUE, zorder=3, label="Before taxes and levies", edgecolor=SURFACE, lw=1.5)
    ax.scatter(t["ratio_incl"], y, s=42, color=ORANGE, zorder=3, label="All taxes and levies included", edgecolor=SURFACE, lw=1.5)
    labels = [name(g) + (f" ({p})" if g == "UK" else "") for g, p in zip(t["geo"], t["period"])]
    ax.set_yticks(y, labels)
    ax.tick_params(axis="y", length=0)
    ax.axvline(A.BREAKEVEN_CENTRAL, color=INK2, lw=1, ls=(0, (4, 3)), zorder=0)
    ax.grid(axis="x", color=GRID, lw=0.8, zorder=0)
    ax.set_xlabel("Electricity price ÷ gas price")
    ax.set_title("How taxes, levies and support move the ratio", loc="left")
    ax.legend(frameon=False, loc="upper left", fontsize=9)
    _note(fig, "Sorted by the change taxes, levies and support make. Towards the top, policy costs fall more on "
          "electricity and raise the ratio; towards the bottom they lower it (gas taxed relatively more, or electricity "
          "supported). "
          "Same semesters and bands as the first chart; dashed: central break-even.", 120)
    fig.tight_layout(rect=(0, 0.06, 1, 1))
    path = FIGURES / "tax_effect_on_ratio.png"
    fig.savefig(path)
    plt.close(fig)
    return path.name


def fig_uk_crosscheck(cc: pd.DataFrame) -> str:
    fig, ax = plt.subplots(figsize=(9, 4.2))
    ax.axvspan(2021.5, 2023.5, color=BAND, lw=0, zorder=0)
    ax.axhline(0, color=INK2, lw=0.8)
    for fuel, colour, label in [("electricity", BLUE, "Electricity"), ("gas", ORANGE, "Gas")]:
        s = cc[cc["fuel"] == fuel]
        ax.plot(s["year"], s["gap_pct"], color=colour, lw=2, marker="o", ms=4.5, label=label, zorder=3)
        ax.text(s["year"].iloc[-1] + 0.25, s["gap_pct"].iloc[-1], label, fontsize=9, va="center", color=INK)
    ax.text(2022.5, ax.get_ylim()[0] + 0.6, "2022-23", fontsize=8, color=INK2, ha="center", va="bottom")
    ax.set_xlim(cc["year"].min() - 0.5, cc["year"].max() + 1.6)
    ax.set_ylabel("Semester series vs bills series (%)")
    ax.set_title("Two DESNZ series for UK household prices diverge in 2022-23", loc="left")
    ax.grid(axis="y", color=GRID, lw=0.8, zorder=0)
    ax.legend(frameon=False, loc="upper left", fontsize=9)
    _note(fig, "Annual mean of DESNZ's half-yearly EU-format prices (QEP 5.6.2, 5.10.2, tax included) against unit rate "
          "plus fixed cost from QEP 2.2.4 and 2.3.4, spread over 3,750 kWh (electricity) or 12,000 kWh (gas).", 135)
    fig.tight_layout(rect=(0, 0.06, 1, 1))
    path = FIGURES / "uk_series_crosscheck.png"
    fig.savefig(path)
    plt.close(fig)
    return path.name


def analyse(prices, ratio, cc, gb_methods, checks) -> None:
    FIGURES.mkdir(parents=True, exist_ok=True)
    latest, eu_latest = latest_by_country(ratio)
    eu = latest[latest["geo"].isin(EU27)]
    uk = latest[latest["geo"] == "UK"].iloc[0]
    c = _central(ratio)
    eu27 = c[(c["geo"] == "EU27_2020")].set_index("period")["ratio"]
    eu27_now = eu27[eu_latest]
    same = c[(c["period"] == uk["period"]) & (c["geo"].isin(EU27) | (c["geo"] == "UK"))]
    rank_uk = int((same["ratio"] > uk["ratio"]).sum()) + 1
    eu27_uk_period = eu27[uk["period"]]
    cheaper = eu[eu["ratio"] < A.BREAKEVEN_CENTRAL]
    sure = eu[eu["ratio"] < A.BREAKEVEN_LOW]
    dearer = eu[eu["ratio"] >= A.BREAKEVEN_HIGH]
    hp_cost_uk = uk["ratio"] * A.BOILER_EFF_CENTRAL / A.SPF_CENTRAL
    hp_cost_eu = eu27_now * A.BOILER_EFF_CENTRAL / A.SPF_CENTRAL

    t = tax_effect(ratio)
    uk_t = t[t["geo"] == "UK"].iloc[0]
    up = t[t["tax_effect_pct"] > 0]
    eu_t = _central(ratio, "X_TAX")
    eu27_excl_uk_period = eu_t[(eu_t["geo"] == "EU27_2020") & (eu_t["period"] == uk["period"])]["ratio"].iloc[0]
    w2 = next(x for x in checks if x.id == "W2")
    w2_countries = sorted({r["geo"] for r in w2.examples}) if w2.failed <= len(w2.examples) else None

    dd = _central(ratio, "I_TAX", "DD")
    dd_now = dd[(dd["period"] == eu_latest) & dd["geo"].isin(EU27)]
    dd_cheaper = int((dd_now["ratio"] < A.BREAKEVEN_CENTRAL).sum())
    uk_dd = dd[(dd["geo"] == "UK") & (dd["period"] == uk["period"])]["ratio"].iloc[0]

    gm = gb_methods.set_index("year")
    last_year = int(gm.index.max())
    cc_e = cc[cc["fuel"] == "electricity"].set_index("year")
    cc_g = cc[cc["fuel"] == "gas"].set_index("year")
    normal = cc[~cc["year"].isin([2022, 2023])]

    nxt = next_update()
    figs = [fig_latest(latest, eu_latest), fig_over_time(ratio), fig_tax(t), fig_uk_crosscheck(cc)]
    ck = {x.id: x for x in checks}

    lines = [
        "# Findings",
        "",
        f"Generated from the data on every build. Prices are household averages (all taxes, levies and support "
        f"included unless stated) for a medium consumer: electricity band DC, gas band D2. A heat pump with a "
        f"seasonal performance factor of {A.SPF_CENTRAL} is cheaper to run than a gas boiler that is {A.BOILER_EFF_CENTRAL:.0%} efficient "
        f"boiler when the electricity-to-gas price ratio is below {A.BREAKEVEN_CENTRAL:.2f}. Across plausible "
        f"installations the break-even runs from {A.BREAKEVEN_LOW:.2f} to {A.BREAKEVEN_HIGH:.2f}.",
        "",
        f"## 1. In {eu_latest}, a typical heat pump was cheaper to run than gas in {len(cheaper)} of {len(eu)} EU countries",
        "",
        f"- The EU27 ratio was **{eu27_now:.2f}**, so heat from a typical heat pump cost about "
        f"{hp_cost_eu:.0%} of heat from a gas boiler.",
        f"- In {len(sure)} countries the ratio was below {A.BREAKEVEN_LOW:.2f}, where even a poorly performing heat pump "
        f"beats a good boiler: {', '.join(name(g) for g in sure.sort_values('ratio')['geo'])}.",
        f"- {len(dearer)} EU country was above {A.BREAKEVEN_HIGH:.2f}, where even a good heat pump loses: "
        f"{', '.join(name(g) for g in dearer['geo'])}." if len(dearer) == 1 else
        f"- {len(dearer)} EU countries were above {A.BREAKEVEN_HIGH:.2f}.",
        f"- {ck['W8'].detail} Missing: " + "; ".join(f"{name(r['geo'])} ({r['reason']})" for r in ck["W8"].examples) + ".",
        "",
        f"![Ratio by country]({'figures/' + figs[0]})",
        "",
        f"## 2. The UK has one of the highest ratios in Europe: {uk['ratio']:.2f} in {uk['period']}",
        "",
        f"- In {uk['period']} (the UK's latest semester) it ranked {rank_uk} of {len(same)} among EU countries and the UK, "
        f"against {eu27_uk_period:.2f} for the EU27. At this ratio a typical heat pump costs about {hp_cost_uk - 1:.0%} more "
        "to run than a gas boiler." + (f" DESNZ's next update of these tables is due {nxt}; the weekly refresh picks it up."
                                        if nxt else ""),
        f"- Taxes and levies push the UK ratio up by **{uk_t['tax_effect_pct']:.0f}%** (from {uk_t['ratio_excl']:.2f} before "
        f"taxes). Across the EU27 in the same semester they move it the other way: {eu27_excl_uk_period:.2f} before taxes, "
        f"{eu27_uk_period:.2f} after.",
        f"- Even before taxes the UK ratio ({uk_t['ratio_excl']:.2f}) is above the EU27's ({eu27_excl_uk_period:.2f}).",
        f"- Using unit rates only, which is what a household that switches from gas saves per kWh, the UK ratio for "
        f"{last_year} is {gm.loc[last_year, 'ratio_unit_rate']:.2f}, against {gm.loc[last_year, 'ratio_semester_avg_price']:.2f} "
        "on average prices. Leaving the gas grid also removes the gas standing charge, which this ratio does not count.",
        "",
        f"![Ratio over time]({'figures/' + figs[1]})",
        "",
        "## 3. Taxes, levies and support decide which side of break-even many countries fall",
        "",
        f"- In {len(up)} of {len(t)} countries shown, policy costs raise the ratio; in the rest they lower it.",
        f"- Biggest rise: " + ", ".join(f"{name(r.geo)} (+{r.tax_effect_pct:.0f}%)" for r in t.tail(3)[::-1].itertuples()) + ".",
        f"- Biggest fall: " + ", ".join(f"{name(r.geo)} ({r.tax_effect_pct:.0f}%)" for r in t.head(3).itertuples()) + ".",
        f"- In {ck['W2'].failed} cases since 2020 (a country, semester and consumption band) the price with all taxes "
        "included was *below* the price before taxes, because government support or a fixed refund was recorded as "
        "negative tax. For those rows the 'tax-inclusive' ratio measures support policy as much as tax (rule W2 lists "
        "them).",
        "",
        f"![Tax effect]({'figures/' + figs[2]})",
        "",
        "## 4. A larger electricity user, closer to an electrically heated home, sees a lower ratio",
        "",
        f"- Using electricity band DD (5,000-14,999 kWh/yr), {dd_cheaper} of {len(dd_now)} EU countries fall below the central "
        f"break-even in {eu_latest}, against {len(cheaper)} on band DC. The UK ratio falls from {uk['ratio']:.2f} to {uk_dd:.2f}.",
        "",
        "## 5. Two official UK series disagree during the energy crisis",
        "",
        f"- In other years DESNZ's half-yearly UK prices (the series that continues Eurostat's) sit a median "
        f"{abs(normal['gap_pct'].median()):.0f}% {'below' if normal['gap_pct'].median() < 0 else 'above'} its separate "
        "bills series. That gap is expected: the bills series covers standard tariffs only and is weighted differently.",
        f"- In 2023 the gap jumps to **{cc_e.loc[2023, 'gap_pct']:+.0f}%** for electricity and **{cc_g.loc[2023, 'gap_pct']:+.0f}%** for "
        f"gas (2022: {cc_e.loc[2022, 'gap_pct']:+.0f}% and {cc_g.loc[2022, 'gap_pct']:+.0f}%). The electricity figure for "
        f"2023-S1 is {cc_e.loc[2023, 's1'] * 100:.1f}p/kWh.",
        "- The bills tables state that they incorporate the Energy Price Guarantee (October 2022 to June 2023). The "
        "half-yearly tables do not say how UK support was recorded. Until that is confirmed with DESNZ, UK values for "
        "2022-S2 and 2023-S1 should be read with caution. The ratio is less affected because both fuels move: for 2023 "
        f"it is {gm.loc[2023, 'ratio_semester_avg_price']:.2f} on the half-yearly series and "
        f"{gm.loc[2023, 'ratio_bills_avg_price']:.2f} on the bills series.",
        "",
        f"![UK cross-check]({'figures/' + figs[3]})",
        "",
        "## What this does not show",
        "",
        "- Average prices include standing charges spread over each band's consumption, so they are not the marginal "
        "price a switching household faces (see finding 2 for the UK unit-rate comparison).",
        "- Heat-pump tariffs and time-of-use pricing, which can cut a heat pump's running cost well below the standard "
        "price, are not in these statistics.",
        "- Running cost is not the whole decision: installation cost, grants and the building matter as much.",
    ]
    (REPORTS / "findings.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    t.round(4).to_csv(REPORTS / "tax_effect_latest.csv", index=False)

# Data dictionary

All files are UTF-8 CSV with a header row. Missing values are empty cells. Periods are half-years written `YYYY-S1` (January-June) and `YYYY-S2` (July-December). Country codes are Eurostat's (`EL` is Greece, `UK` the United Kingdom); `EU27_2020` and `EA` are Eurostat's EU and euro-area aggregates.

## household_prices.csv

One row per country, half-year, fuel, consumption band, tax level and currency.

| Column | Type | Meaning |
|---|---|---|
| `geo` | text | Eurostat country code |
| `country` | text | Country name |
| `period` | text | Half-year |
| `fuel` | text | `electricity` or `gas` |
| `band` | text | Electricity: `DA` (<1,000 kWh/yr), `DB` (1,000-2,499), `DC` (2,500-4,999), `DD` (5,000-14,999), `DE` (15,000+), `ALL`. Gas: `D1` (<20 GJ/yr), `D2` (20-199 GJ), `D3` (200+ GJ), `ALL` |
| `tax` | text | `X_TAX` excluding taxes and levies; `X_VAT` excluding VAT and recoverable taxes; `I_TAX` all taxes and levies included (support recorded as negative tax from 2021) |
| `currency` | text | `EUR` or `NAC` (national currency; GBP for the UK) |
| `price_per_kwh` | number | Price per kWh in `currency`. Gas kWh are gross calorific value |
| `flag` | text | Eurostat observation flag: `e` estimated, `p` provisional, `d` definition differs, `b` break in series; empty if none |
| `confidential` | true/false | Eurostat marked the value confidential (no value published) |
| `source_id` | text | Source in `data/raw/manifest.json` |
| `source_last_update` | text | Eurostat's last-update timestamp for the value; empty for DESNZ rows |

## electricity_gas_ratio.csv

One row per country, half-year, tax level, currency and electricity band. Gas is always band D2.

| Column | Type | Meaning |
|---|---|---|
| `geo`, `country`, `period`, `tax`, `currency` | | As above |
| `elec_band` | text | `DC` (central case) or `DD` (sensitivity) |
| `elec_price_per_kwh`, `gas_price_per_kwh` | number | The two prices |
| `ratio` | number | Electricity price divided by gas price |
| `elec_flag`, `gas_flag` | text | Eurostat flags on each input |
| `elec_source`, `gas_source` | text | Source of each input |
| `hp_to_boiler_running_cost` | number | Heat-pump running cost as a share of gas-boiler running cost at central assumptions (SPF 2.8, boiler 85%). Below 1: heat pump cheaper |
| `hp_cheaper_central` | true/false | `ratio` below the central break-even of 3.29 |
| `hp_verdict` | text | `cheaper` (ratio below 2.78), `dearer` (4.38 or above), otherwise `depends on install` |

## price_components.csv

Eurostat's annual breakdown, 2017 onward.

| Column | Meaning |
|---|---|
| `geo`, `year`, `fuel`, `band`, `currency` | As above; `year` is a calendar year |
| `component` | `NRG_SUP` energy and supply; `NETC` network; `TAX_FEE_LEV_CHRG` taxes, fees, levies and charges; `VAT`; detailed taxes (`TAX_RNW`, `TAX_CAP`, `TAX_ENV`, `TAX_NUC`) and the matching `_ALLOW` allowances; `ALLOW_OTH` other allowances; `OTH` other |
| `value_per_kwh` | Component value per kWh |
| `flag`, `source_id` | As above |

## uk_ratio_methods.csv

| Column | Meaning |
|---|---|
| `year` | Calendar year |
| `ratio_semester_avg_price` | Ratio of the two half-year average prices from DESNZ's Eurostat-format tables, averaged over the year |
| `ratio_bills_avg_price` | Ratio of unit rate plus fixed cost spread over 3,750 kWh (electricity) or 12,000 kWh (gas), from QEP 2.2.4 and 2.3.4 |
| `ratio_unit_rate` | Ratio of unit rates only: the saving per kWh for a household that switches |

## uk_series_crosscheck.csv

| Column | Meaning |
|---|---|
| `year`, `fuel` | |
| `s1`, `s2`, `semester_mean` | DESNZ half-year prices (GBP/kWh, tax included) and their unweighted mean |
| `unit_gbp_per_kwh`, `fixed_gbp_per_year` | DESNZ bills series |
| `bills_avg_price` | Unit rate plus fixed cost spread over the representative consumption |
| `bills_avg_price_low_use`, `bills_avg_price_high_use` | The same at two-thirds and four-thirds of that consumption |
| `gap_pct` | Half-year series against bills series, per cent |
| `gap_pct_range` | The gap across the low- and high-use cases |
| `provisional`, `revised` | DESNZ's `p` and `r` markers on the year |

## uk_splice_overlap.csv

Every UK value published by both Eurostat and DESNZ: `period`, `fuel`, `band`, `tax`, `eurostat_gbp_per_kwh`, `desnz_gbp_per_kwh`, `diff_pct`.

## fx_check.csv

For each country with its own currency and each half-year: `implied` (national-currency price divided by euro price, median across that country's rows), `ecb` (mean of the ECB's six monthly averages), `diff_pct`.

## cleaning_log.csv

Every value a cleaning rule set to, or left, missing: the key columns, `action`, `reason` and `source_id`.

## build_info.json

The raw snapshot's fetch time and SHA-256 hashes, the heat-pump assumptions with their sources, and row counts.

# Methods

This document explains how each published number is produced and why each choice was made. Where a choice changes the answer, the alternative is published alongside it.

## 1. What is being measured

The electricity-to-gas price ratio is the household price of a kWh of electricity divided by the household price of a kWh of gas, in the same country, half-year, tax treatment and currency. It is unit-free, so it does not depend on the currency used (rule W1 checks this).

It matters for electrification because it decides the running cost of a heat pump relative to a gas boiler:

```
heat pump cost per kWh of heat  = electricity price / SPF
boiler cost per kWh of heat     = gas price / boiler efficiency

heat pump cheaper  <=>  electricity price / gas price  <  SPF / boiler efficiency
```

## 2. Sources and what each contributes

| Source | Contribution | Coverage used |
|---|---|---|
| Eurostat nrg_pc_204 | Electricity prices for household consumers | 2007-S2 to latest, all countries, bands DA-DE, three tax levels, EUR and national currency |
| Eurostat nrg_pc_202 | Gas prices for household consumers (kWh, gross calorific value) | As above, bands D1-D3 |
| Eurostat nrg_pc_204_c, nrg_pc_202_c | Annual price components (energy and supply, network, taxes, levies, allowances, VAT) | 2017 onward, bands DC, DD (electricity) and D2 (gas) |
| DESNZ QEP 5.6.2, 5.6.3, 5.10.2 | UK prices compiled with Eurostat's methodology | 2008-S1 to latest; used for the UK after 2020-S1 |
| DESNZ QEP 2.2.4, 2.3.4 | UK calendar-year unit rate and fixed cost, standard tariffs | 2010 to latest; cross-check only |
| ECB EXR | Monthly average euro reference rates | 2007 onward; FX check and UK euro values |

The Eurostat extracts use the 2007-S2 methodology only. Before that Eurostat priced a single "standard consumer" at two dates a year, which measures something different; DESNZ's own tables mark the same break.

## 3. Consumption bands

- **Electricity band DC** (2,500-4,999 kWh a year) is the central case. It is Eurostat's and DESNZ's "medium" household and the band most often used in international comparisons.
- **Gas band D2** (20-199 GJ a year, roughly 5,600-55,600 kWh) contains a typical gas-heated home.
- **Electricity band DD** (5,000-14,999 kWh) is published as a sensitivity. A household that has replaced a gas boiler with a heat pump uses more electricity and moves up a band, where the average price is usually lower because the standing charge is spread over more kWh.

The two fuels are compared for typical households of each, not for one household. That is the standard construction of this ratio and the reason the band sensitivity is published.

## 4. Tax levels

Eurostat publishes three:

- `X_TAX`: excluding taxes, levies and VAT (energy and supply plus network costs)
- `X_VAT`: excluding VAT and other recoverable taxes
- `I_TAX`: all taxes and levies included

Since 2021 Eurostat includes **subsidies and allowances** in the tax component. Where government support exceeded taxes and levies, as in many countries in 2022 and 2023, `I_TAX` is lower than `X_TAX`. The Netherlands' fixed annual energy-tax refund has the same effect every year, strong enough to make the smallest band's tax-inclusive price negative. Rule W2 lists every such case in the bands used for the ratio, so a user can tell where the tax-inclusive ratio measures support policy rather than tax policy.

DESNZ publishes "including tax" and "excluding tax" for the UK. Its excluding-tax figures have removed environmental and social levies as well as VAT since 2015, which matches Eurostat's `X_TAX`; no `X_VAT` exists for the UK after 2020-S1.

## 5. Cleaning rules

Every value a rule touches is written to `data/processed/cleaning_log.csv`.

1. **Exact zeros become missing.** Eurostat publishes household gas prices of exactly 0 for Albania and North Macedonia, where no household gas is priced. Left in, they would produce infinite ratios.
2. **Confidential cells stay missing** and are marked `confidential = True`. Poland's household gas prices have been confidential since 2024-S1.
3. **Negative tax-inclusive prices are kept.** They occur only in the two smallest electricity bands (the Netherlands and Czechia) and are real. The blocking range check (B2) exempts those bands and applies everywhere else.
4. **Flagged values are kept, with their flag.** Eurostat's `e` (estimated), `p` (provisional), `d` (definition differs) and `b` (break in series) travel into the ratio table as `elec_flag` and `gas_flag`.

## 6. Continuing the UK series

Eurostat's last UK observation is 2020-S1. DESNZ states that it collects UK data "using the same methodology" and publishes it in pence per kWh in QEP tables 5.6.x and 5.10.x. Before joining the two:

- **Rule B3 (blocking)** compares every value both publish, 2008-S1 to 2020-S1, using Eurostat's national-currency (GBP) figures so no exchange rate is involved. All 150 agree within 0.52%. If any differed by more than 1% the build would stop.
- After 2020-S1, UK prices come from DESNZ. Pence are converted to GBP per kWh (Eurostat's national-currency convention) and to euro with the ECB semester-average rate, the convention Eurostat uses (rule W4 shows Eurostat's own euro values match this rate with a median gap of 0.01%).

## 7. The UK cross-check, and what it found

DESNZ publishes a second, independent UK series: calendar-year average unit rate and fixed cost for standard tariffs (QEP 2.2.4 and 2.3.4). To compare it with the half-yearly series, the fixed cost is spread over a consumption in the same band (3,750 kWh electricity, 12,000 kWh gas, with plus or minus a third reported as a range), and the two half-years are averaged without weighting, as DESNZ does in its annual tables.

From 2010 to 2021 and again in 2024-25 the half-yearly series sits a few per cent below the bills series, which is expected: the bills series covers standard tariffs only, while the half-yearly series covers all tariffs, including cheaper fixed deals. In 2022 the gap turns positive and in 2023 it reaches +17% for electricity and +10% for gas, outside the range of every other year even with the consumption sensitivity.

The bills tables state that they "incorporate the Energy Price Guarantee from October 2022 but do not reflect payments made through the Energy Bills Support Scheme". The half-yearly tables say nothing about how UK support was recorded. That is the most likely place for the difference, but it is not confirmed. The project therefore:

- keeps the DESNZ half-yearly values as published (they are the series consistent with Eurostat's method)
- flags 2022-S2 and 2023-S1 for caution in the findings
- publishes the UK ratio on both series (`uk_ratio_methods.csv`): for 2023 it is 3.86 on the half-yearly series and 3.63 on the bills series

The next step is to ask DESNZ how the Energy Price Guarantee was treated in tables 5.6.x and 5.10.x.

## 8. Heat-pump comparison

| Assumption | Central | Range | Source |
|---|---|---|---|
| Heat-pump seasonal performance factor (SPF) | 2.8 | 2.5-3.5 | Energy Systems Catapult for DESNZ (2023), Electrification of Heat Demonstration Project, interim insights: median ASHP SPF 2.80 |
| Gas boiler efficiency, gross calorific value | 85% | 80-90% | GASTEC for the Energy Saving Trust (2009), in-situ monitoring of condensing boilers: means of 82.5% (combi) and 85.3% (regular), higher calorific value basis |

Eurostat gas prices are per kWh of gross calorific value, so the boiler efficiency must be on the same basis.

- Central break-even ratio: 2.8 / 0.85 = **3.29**
- `hp_to_boiler_running_cost` = ratio x 0.85 / 2.8 (below 1 means the heat pump is cheaper)
- `hp_verdict`: "cheaper" below 2.78 (a poor heat pump against a good boiler still wins), "dearer" at or above 4.38 (a good heat pump against a poor boiler still loses), otherwise "depends on install"

## 9. Average and marginal prices

Eurostat's price is total value divided by total kWh within a band, so it includes standing charges. A household that switches to a heat pump faces the **unit rate** at the margin, and if it leaves the gas grid it also stops paying the gas standing charge. For the UK, where DESNZ publishes unit rates, `uk_ratio_methods.csv` gives the unit-rate ratio as well (4.01 in 2025, against 4.24 on average prices). For other countries the components table separates network costs but not fixed from variable charges, so the average-price ratio is what can be published consistently.

## 10. What the dataset does not cover

- Heat-pump and time-of-use tariffs are not in official price statistics.
- Installation costs, grants and building fabric are outside scope.
- Countries without household gas prices (Cyprus, Finland, Malta) have no ratio.

## 11. Decisions log

| Decision | Alternatives considered | Why |
|---|---|---|
| Eurostat SDMX-CSV rather than JSON-stat | JSON-stat; bulk TSV | CSV carries flags and confidentiality per row, is easy to diff in git, and fits in one request per table |
| Find DESNZ files via the GOV.UK content API | Hard-coded asset URLs | Asset URLs change on every update; the content API gives the current one by title |
| Join the UK series only if B3 passes | Join unconditionally | A splice that silently shifted levels would corrupt every UK trend |
| Treat exact zeros as missing | Keep zeros | A zero price for a fuel with no market is a placeholder, not a price |
| Keep negative tax-inclusive prices | Drop or clip them | They are real (refunds larger than tiny bills) and only occur outside the ratio's bands |
| Publish both DC and DD electricity bands | DC only | Which band applies to an electrified home changes the answer in several countries |
| Make warnings non-blocking | Block on every rule | Most warnings describe real features of the data that users need to see, not errors |

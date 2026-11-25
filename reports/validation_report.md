# Validation report

Raw snapshot fetched 2026-11-25T00:14:30Z. Every rule below runs on every build; a failed blocking rule stops the build before anything is written.

| Rule | Check | Severity | Checked | Flagged | Result |
|---|---|---|---:|---:|---|
| B1 | One row per country, semester, fuel, band, tax level and currency; valid codes | blocking | 67,053 | 0 | pass |
| B2 | Prices used in the ratio, and every pre-tax price, are above zero and below EUR 2/kWh | blocking | 19,739 | 0 | pass |
| B3 | DESNZ and Eurostat agree on UK prices where both publish | blocking | 150 | 0 | pass |
| W1 | The ratio is the same whether computed in euro or in national currency | warning | 6,694 | 4 | see below |
| W2 | Tax-inclusive price is at least the tax-exclusive price (bands used in the ratio) | warning | 3,914 | 70 | see below |
| W3 | Larger consumers do not pay more than 5% above smaller ones (tax included) | warning | 7,779 | 635 | see below |
| W4 | Eurostat's euro prices match its national-currency prices at the ECB semester-average rate | warning | 439 | 0 | pass |
| W5 | Ratios built on flagged Eurostat values | warning | 1,199 | 32 | see below |
| W6 | Semester-on-semester price moves above 50% | warning | 2,617 | 35 | see below |
| W7 | UK semester prices agree with DESNZ's separate bills series | warning | 32 | 2 | see below |
| W8 | EU countries with a ratio in the latest semester (2026-S1) | warning | 27 | 4 | see below |

## B1. One row per country, semester, fuel, band, tax level and currency; valid codes

Duplicate keys or unknown period, tax or currency codes.

## B2. Prices used in the ratio, and every pre-tax price, are above zero and below EUR 2/kWh

Outside this range points to a unit or parsing error. Tax-inclusive prices in the two smallest electricity bands are exempt: they can be negative when a fixed annual refund exceeds a very small bill (see W2).

## B3. DESNZ and Eurostat agree on UK prices where both publish

Before joining the DESNZ UK series onto Eurostat's, both must agree where they overlap. 150 overlapping values (2008-S1 to 2020-S1); largest difference 0.52%. Tolerance 1.0%.

## W1. The ratio is the same whether computed in euro or in national currency

A unit-free ratio should not depend on currency; differences beyond rounding of the published 4-decimal prices would mean the two fuels were converted at different rates.

Rows:

| geo   | period   | tax   | elec_band   |   ratio_eur |   ratio_nac |   diff_pct |
|:------|:---------|:------|:------------|------------:|------------:|-----------:|
| GE    | 2021-S1  | X_TAX | DC          |        5.35 |      5.3794 |    -0.5465 |
| GE    | 2021-S1  | X_TAX | DD          |        5.83 |      5.8593 |    -0.5    |
| GE    | 2021-S1  | X_VAT | DC          |        5.35 |      5.3794 |    -0.5465 |
| GE    | 2021-S1  | X_VAT | DD          |        5.83 |      5.8593 |    -0.5    |

## W2. Tax-inclusive price is at least the tax-exclusive price (bands used in the ratio)

Eurostat includes subsidies and allowances in the tax component from 2021, so where government support exceeded taxes and levies the 'all taxes included' price falls below the price before taxes. The Netherlands' fixed annual energy-tax refund has the same effect (DESNZ notes it). For these rows the tax-inclusive ratio measures support policy as much as tax policy. By country, first-last semester (count): AT 2023-S1-2024-S2 (4); BG 2022-S1-2022-S1 (1); CZ 2022-S2-2022-S2 (1); EL 2022-S1-2022-S2 (5); IE 2022-S1-2025-S1 (13); IT 2022-S2-2023-S1 (2); LU 2022-S2-2025-S2 (17); LV 2022-S1-2023-S1 (5); NL 2020-S2-2026-S1 (14); NO 2022-S1-2026-S1 (6); PT 2023-S1-2023-S1 (2).

First 12 of 70:

| geo   | period   | fuel        | band   |   X_TAX |   I_TAX |   net_taxes_per_kwh |
|:------|:---------|:------------|:-------|--------:|--------:|--------------------:|
| NL    | 2020-S2  | electricity | DC     |  0.1356 |  0.1351 |             -0.0005 |
| NL    | 2021-S1  | electricity | DC     |  0.1357 |  0.1284 |             -0.0073 |
| NL    | 2021-S2  | electricity | DC     |  0.1484 |  0.1436 |             -0.0048 |
| BG    | 2022-S1  | gas         | D2     |  0.0798 |  0.0764 |             -0.0034 |
| EL    | 2022-S1  | electricity | DC     |  0.295  |  0.2101 |             -0.0849 |
| EL    | 2022-S1  | electricity | DD     |  0.2835 |  0.2592 |             -0.0243 |
| EL    | 2022-S1  | gas         | D2     |  0.0922 |  0.0821 |             -0.0101 |
| IE    | 2022-S1  | electricity | DC     |  0.2693 |  0.2324 |             -0.0369 |
| IE    | 2022-S1  | electricity | DD     |  0.2335 |  0.2287 |             -0.0048 |
| LV    | 2022-S1  | electricity | DC     |  0.1779 |  0.1759 |             -0.002  |
| LV    | 2022-S1  | electricity | DD     |  0.1711 |  0.1703 |             -0.0008 |
| LV    | 2022-S1  | gas         | D2     |  0.0593 |  0.0462 |             -0.0131 |

## W3. Larger consumers do not pay more than 5% above smaller ones (tax included)

Fixed charges spread over more kWh normally make the average price fall with consumption. Exceptions come from rising-block tariffs, refunds that make the smallest bands negative, or support capped at a volume, so they are reported rather than corrected. Most frequent: NL (110), MT (78), EL (72), IT (53), GE (47), HU (35), XK (33), RS (28).

First 12 of 635:

| geo   | period   | fuel        | lower_band   | higher_band   |   lower_price |   higher_price |
|:------|:---------|:------------|:-------------|:--------------|--------------:|---------------:|
| AL    | 2025-S1  | electricity | DA           | DB            |        0.1034 |         0.1156 |
| AT    | 2023-S2  | electricity | DD           | DE            |        0.2808 |         0.2949 |
| AT    | 2024-S2  | electricity | DC           | DD            |        0.2437 |         0.2568 |
| BA    | 2023-S2  | electricity | DD           | DE            |        0.0836 |         0.0898 |
| BE    | 2022-S2  | gas         | D2           | D3            |        0.1363 |         0.1484 |
| BE    | 2025-S2  | electricity | DD           | DE            |        0.3274 |         0.3463 |
| BG    | 2007-S2  | gas         | D1           | D2            |        0.0306 |         0.0323 |
| BG    | 2008-S1  | gas         | D1           | D2            |        0.0324 |         0.0354 |
| BG    | 2008-S2  | electricity | DD           | DE            |        0.0818 |         0.09   |
| BG    | 2008-S2  | gas         | D2           | D3            |        0.0391 |         0.0419 |
| CY    | 2008-S2  | electricity | DB           | DC            |        0.1906 |         0.204  |
| CY    | 2009-S1  | electricity | DB           | DC            |        0.131  |         0.1558 |

## W4. Eurostat's euro prices match its national-currency prices at the ECB semester-average rate

Implied rate = national-currency price / euro price, compared with the mean of the ECB's six monthly averages. Tolerance 2.0%.

## W5. Ratios built on flagged Eurostat values

Flags: e = estimated, p = provisional, d = definition differs, b = break in series. Counts across both fuels: {'e': 25, 'd': 4, 'p': 4, 'b': 1}. Flagged values are kept and the flag carried into the ratio table, so users can exclude them.

First 12 of 32:

| geo   | period   |   ratio | elec_flag   | gas_flag   |
|:------|:---------|--------:|:------------|:-----------|
| AT    | 2022-S2  |  1.919  | e           |            |
| AT    | 2023-S1  |  1.7006 | e           |            |
| AT    | 2023-S2  |  1.8605 | e           |            |
| AT    | 2024-S1  |  1.9804 | e           |            |
| AT    | 2024-S2  |  1.9701 | e           |            |
| AT    | 2025-S1  |  2.3811 | e           |            |
| AT    | 2025-S2  |  2.6798 | e           |            |
| EL    | 2017-S1  |  3.0554 |             | p          |
| EL    | 2018-S1  |  3.1429 |             | e          |
| IT    | 2016-S2  |  2.6981 |             | p          |
| RO    | 2017-S1  |  3.9538 |             | e          |
| RO    | 2017-S2  |  4.1851 |             | e          |

## W6. Semester-on-semester price moves above 50%

Not errors in themselves (2022 was extraordinary) but each one was looked at before publication.

First 12 of 35:

| geo   | period   | fuel        |   prev |   price_per_kwh |   change |
|:------|:---------|:------------|-------:|----------------:|---------:|
| NL    | 2022-S2  | electricity | 0.0336 |          0.1418 |   3.2202 |
| NL    | 2023-S1  | electricity | 0.1418 |          0.3572 |   1.519  |
| LV    | 2022-S2  | gas         | 0.0462 |          0.1111 |   1.4048 |
| EL    | 2021-S2  | gas         | 0.0449 |          0.1014 |   1.2584 |
| UK    | 2022-S2  | gas         | 0.066  |          0.1453 |   1.2036 |
| LT    | 2022-S2  | gas         | 0.0587 |          0.1288 |   1.1942 |
| MK    | 2022-S1  | gas         | 0.057  |          0.121  |   1.1228 |
| RO    | 2022-S2  | gas         | 0.0611 |          0.1265 |   1.0704 |
| EL    | 2022-S2  | gas         | 0.0821 |          0.1599 |   0.9476 |
| MD    | 2021-S2  | gas         | 0.0243 |          0.047  |   0.9342 |
| BG    | 2021-S2  | gas         | 0.0368 |          0.0708 |   0.9239 |
| MD    | 2022-S2  | electricity | 0.1172 |          0.2245 |   0.9155 |

## W7. UK semester prices agree with DESNZ's separate bills series

Annual mean of the two semester prices (tax included) against unit rate plus fixed cost spread over 3,750 kWh (electricity) or 12,000 kWh (gas). Tolerance 10.0%. The two series differ in scope (all tariffs in a consumption band against standard tariffs only) and weighting, so small gaps are expected; large ones point to a difference in how support was recorded.

Rows:

|   year | fuel        |     s1 |     s2 |   semester_mean |   unit_gbp_per_kwh |   fixed_gbp_per_year |   bills_avg_price |   gap_pct | gap_pct_range   |
|-------:|:------------|-------:|-------:|----------------:|-------------------:|---------------------:|------------------:|----------:|:----------------|
|   2023 | electricity | 0.5003 | 0.3239 |          0.4121 |             0.3038 |              180.568 |            0.3519 |   17.0976 | +9.6 to +21.2   |
|   2023 | gas         | 0.1368 | 0.077  |          0.1069 |             0.088  |              108.292 |            0.0971 |   10.1124 | +5.2 to +12.7   |

## W8. EU countries with a ratio in the latest semester (2026-S1)

23 of 27 EU countries have both prices in 2026-S1.

Rows:

| geo   | reason                                |
|:------|:--------------------------------------|
| CY    | no household gas price ever published |
| FI    | no household gas price ever published |
| MT    | no household gas price ever published |
| PL    | gas price confidential since 2024-S1  |

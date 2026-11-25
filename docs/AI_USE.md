# How AI was used, and how its work was checked

The code and documentation in this repository were written with an AI coding assistant (Claude Code). It is good at producing a lot of plausible code and prose quickly, which is exactly why plausible is not accepted as correct here. The project is set up so that its claims can be checked without trusting whoever, or whatever, wrote them.

## Where AI was used

- Exploring the sources: probing the Eurostat, ECB and GOV.UK APIs and reading the structure of the DESNZ workbooks
- Writing the fetch, parse, validation and analysis code, and the tests
- Drafting the README, methods and data dictionary

## The checks that do not depend on the assistant

| Risk | Check |
|---|---|
| A parser reads the wrong cell or column | Values in the tests were checked by hand against the Eurostat API (for example UK electricity, band DC, 2019-S2: EUR 0.2210; German gas, band D2, 2025-S1: EUR 0.1216) |
| Two sources are joined that don't measure the same thing | Rule B3 compares all 150 values Eurostat and DESNZ both publish for the UK and blocks the build on a gap over 1% |
| Currency conversion is wrong | Rule W4 compares the rate implied by Eurostat's own euro and national-currency prices with the ECB's semester average, for 439 country-half-years |
| A validation rule looks reassuring but never fires | Each blocking rule is tested against a planted defect (a duplicated row, a price in cents, a UK series shifted by 5%), and W4 against a wrong exchange rate |
| Findings text drifts from the data | Every number in `reports/findings.md` is computed from the processed tables on each build; none is typed |
| Outputs can't be reproduced | CI rebuilds every table and report from the committed raw files and fails if anything differs |
| Raw data changed without anyone noticing | Every raw file's SHA-256 is in the manifest, verified before each build and in CI |
| An assumption is invented | The heat-pump SPF and boiler efficiency each cite a named field trial, recorded in `build_info.json` |

## Things the checks caught during the build

- The first range check flagged 88 values. They were Eurostat's zero placeholders for household gas in Albania and North Macedonia, and genuine negative prices in the smallest electricity bands in the Netherlands and Czechia. That led to two documented rules: zeros become missing; negatives are kept and the range check is limited to the bands the ratio uses.
- The first version of the tax-ordering rule said support only enters the data from 2021. The data showed the Netherlands below zero net tax since 2020-S2 because of its fixed energy-tax refund, so the description was corrected.
- A first draft compared the UK's latest half-year (2025-S2) with the EU27's (2026-S1). The comparison was changed to use the same half-year for both.
- The cross-check between DESNZ's two UK series surfaced the 2023 divergence described in the methods; it is reported as an open question rather than explained away.

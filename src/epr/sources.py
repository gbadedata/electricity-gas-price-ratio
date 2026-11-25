"""Registry of every upstream source the pipeline reads.

Each source has a stable id, the publisher, the licence the data is released
under, and how to locate it. Eurostat and the ECB have stable query URLs.
DESNZ files move to a new URL each time a table is updated, so they are
located through the GOV.UK content API by attachment title.
"""

from __future__ import annotations

from dataclasses import dataclass, field

EUROSTAT_SDMX = "https://ec.europa.eu/eurostat/api/dissemination/sdmx/2.1/data"
GOVUK_CONTENT = "https://www.gov.uk/api/content"
ECB_DATA = "https://data-api.ecb.europa.eu/service/data"

# Currencies Eurostat reports as national currency (NAC) that the ECB also
# publishes reference rates for. Others (ALL, BAM, GEL, MDL, MKD, RSD, UAH)
# have no ECB rate and are skipped by the FX cross-check, not by the dataset.
ECB_CURRENCIES = [
    "BGN", "CHF", "CZK", "DKK", "GBP", "HRK", "HUF", "ISK",
    "NOK", "PLN", "RON", "SEK", "TRY",
]


@dataclass(frozen=True)
class Source:
    id: str
    publisher: str
    title: str
    licence: str
    kind: str  # "url" or "govuk_attachment"
    url: str = ""
    filename: str = ""
    # For govuk_attachment sources
    govuk_path: str = ""
    attachment_title_contains: tuple[str, ...] = field(default_factory=tuple)


SOURCES: list[Source] = [
    Source(
        id="eurostat_nrg_pc_204",
        publisher="Eurostat",
        title="Electricity prices for household consumers - bi-annual data (from 2007 onwards)",
        licence="CC BY 4.0 (Eurostat reuse policy)",
        kind="url",
        url=f"{EUROSTAT_SDMX}/NRG_PC_204/S.E7000....EUR+NAC.?format=SDMX-CSV&startPeriod=2007-S2",
        filename="nrg_pc_204.csv",
    ),
    Source(
        id="eurostat_nrg_pc_202",
        publisher="Eurostat",
        title="Gas prices for household consumers - bi-annual data (from 2007 onwards)",
        licence="CC BY 4.0 (Eurostat reuse policy)",
        kind="url",
        url=f"{EUROSTAT_SDMX}/NRG_PC_202/S.G3000..KWH..EUR+NAC.?format=SDMX-CSV&startPeriod=2007-S2",
        filename="nrg_pc_202.csv",
    ),
    Source(
        id="eurostat_nrg_pc_204_c",
        publisher="Eurostat",
        title="Electricity prices components for household consumers - annual data (from 2017 onwards)",
        licence="CC BY 4.0 (Eurostat reuse policy)",
        kind="url",
        url=f"{EUROSTAT_SDMX}/NRG_PC_204_C/A.KWH2500-4999+KWH5000-14999..EUR.?format=SDMX-CSV",
        filename="nrg_pc_204_c.csv",
    ),
    Source(
        id="eurostat_nrg_pc_202_c",
        publisher="Eurostat",
        title="Gas prices components for household consumers - annual data (from 2017 onwards)",
        licence="CC BY 4.0 (Eurostat reuse policy)",
        kind="url",
        url=f"{EUROSTAT_SDMX}/NRG_PC_202_C/A..GJ20-199.EUR.KWH.?format=SDMX-CSV",
        filename="nrg_pc_202_c.csv",
    ),
    Source(
        id="desnz_qep_561",
        publisher="Department for Energy Security and Net Zero (DESNZ)",
        title="Domestic electricity prices in the EU for small, medium and large consumers (QEP 5.6.1-5.6.3)",
        licence="Open Government Licence v3.0",
        kind="govuk_attachment",
        govuk_path="/government/statistical-data-sets/international-domestic-energy-prices",
        attachment_title_contains=("Domestic electricity prices in the EU",),
        filename="qep_561.xlsx",
    ),
    Source(
        id="desnz_qep_5101",
        publisher="Department for Energy Security and Net Zero (DESNZ)",
        title="Domestic gas prices in the EU for small, medium and large consumers (QEP 5.10.1-5.10.3)",
        licence="Open Government Licence v3.0",
        kind="govuk_attachment",
        govuk_path="/government/statistical-data-sets/international-domestic-energy-prices",
        attachment_title_contains=("Domestic gas prices in the EU",),
        filename="qep_5101.xlsx",
    ),
    Source(
        id="desnz_qep_224",
        publisher="Department for Energy Security and Net Zero (DESNZ)",
        title="Average unit costs and fixed costs for electricity for UK regions (QEP 2.2.4)",
        licence="Open Government Licence v3.0",
        kind="govuk_attachment",
        govuk_path="/government/statistical-data-sets/annual-domestic-energy-price-statistics",
        attachment_title_contains=("unit costs and fixed costs for electricity",),
        filename="qep_224.xlsx",
    ),
    Source(
        id="desnz_qep_234",
        publisher="Department for Energy Security and Net Zero (DESNZ)",
        title="Average unit costs and fixed costs for gas for GB regions (QEP 2.3.4)",
        licence="Open Government Licence v3.0",
        kind="govuk_attachment",
        govuk_path="/government/statistical-data-sets/annual-domestic-energy-price-statistics",
        attachment_title_contains=("unit costs and fixed costs for gas",),
        filename="qep_234.xlsx",
    ),
    Source(
        id="ecb_exr_monthly",
        publisher="European Central Bank",
        title="ECB euro reference exchange rates, monthly averages",
        licence="ECB statistics reuse terms (free reuse with attribution)",
        kind="url",
        url=(
            f"{ECB_DATA}/EXR/M.{'+'.join(ECB_CURRENCIES)}.EUR.SP00.A"
            "?format=csvdata&startPeriod=2007-01"
        ),
        filename="ecb_exr_monthly.csv",
    ),
]


def by_id(source_id: str) -> Source:
    for s in SOURCES:
        if s.id == source_id:
            return s
    raise KeyError(source_id)

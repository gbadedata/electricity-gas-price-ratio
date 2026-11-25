"""Heat-pump comparison assumptions, kept in one place so every output uses the same ones.

A heat pump is cheaper to run than a gas boiler when

    electricity price / SPF  <  gas price / boiler efficiency

which rearranges to

    electricity price / gas price  <  SPF / boiler efficiency.

So the break-even electricity-to-gas price ratio is SPF / efficiency.
Eurostat gas prices are per kWh of gross calorific value (GCV), so the boiler
efficiency must be on a GCV basis too.
"""

# Seasonal performance factor of an air-source heat pump in real homes.
# Central value: median SPF of 2.80 across ASHPs monitored in the UK
# Electrification of Heat Demonstration Project (Energy Systems Catapult for
# DESNZ, interim findings, 2023).
SPF_CENTRAL = 2.8
SPF_LOW = 2.5
SPF_HIGH = 3.5

# In-use condensing gas boiler efficiency, GCV basis. The Energy Saving Trust
# in-situ field trial (GASTEC, 2009) measured means of 82.5% for combi and
# 85.3% for regular condensing boilers, on the higher (gross) calorific value.
BOILER_EFF_CENTRAL = 0.85
BOILER_EFF_LOW = 0.80
BOILER_EFF_HIGH = 0.90

BREAKEVEN_CENTRAL = SPF_CENTRAL / BOILER_EFF_CENTRAL
# Widest plausible range: a poor heat pump against a good boiler, and the reverse.
BREAKEVEN_LOW = SPF_LOW / BOILER_EFF_HIGH
BREAKEVEN_HIGH = SPF_HIGH / BOILER_EFF_LOW

SOURCES = {
    "spf": (
        "Energy Systems Catapult (2023), Electrification of Heat Demonstration Project: "
        "Interim Insights from Heat Pump Performance Data. Median ASHP SPF 2.80."
    ),
    "boiler": (
        "GASTEC at CRE for the Energy Saving Trust (2009), In-situ monitoring of efficiencies "
        "of condensing boilers and use of secondary heating, final report. Mean 82.5% (combi), "
        "85.3% (regular), higher calorific value basis."
    ),
}

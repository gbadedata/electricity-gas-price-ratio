"""Eurostat geography codes used in the household price tables."""

NAMES = {
    "AL": "Albania", "AT": "Austria", "BA": "Bosnia and Herzegovina", "BE": "Belgium",
    "BG": "Bulgaria", "CY": "Cyprus", "CZ": "Czechia", "DE": "Germany", "DK": "Denmark",
    "EA": "Euro area", "EE": "Estonia", "EL": "Greece", "ES": "Spain",
    "EU27_2020": "EU27", "FI": "Finland", "FR": "France", "GE": "Georgia", "HR": "Croatia",
    "HU": "Hungary", "IE": "Ireland", "IS": "Iceland", "IT": "Italy", "LI": "Liechtenstein",
    "LT": "Lithuania", "LU": "Luxembourg", "LV": "Latvia", "MD": "Moldova", "ME": "Montenegro",
    "MK": "North Macedonia", "MT": "Malta", "NL": "Netherlands", "NO": "Norway", "PL": "Poland",
    "PT": "Portugal", "RO": "Romania", "RS": "Serbia", "SE": "Sweden", "SI": "Slovenia",
    "SK": "Slovakia", "TR": "Türkiye", "UA": "Ukraine", "UK": "United Kingdom", "XK": "Kosovo",
}

AGGREGATES = {"EU27_2020", "EA"}

EU27 = {
    "AT", "BE", "BG", "CY", "CZ", "DE", "DK", "EE", "EL", "ES", "FI", "FR", "HR", "HU",
    "IE", "IT", "LT", "LU", "LV", "MT", "NL", "PL", "PT", "RO", "SE", "SI", "SK",
}


def name(code: str) -> str:
    return NAMES.get(code, code)

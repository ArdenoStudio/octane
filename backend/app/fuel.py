"""Canonical fuel-type identifiers used across scrapers and APIs."""

PETROL_92 = "petrol_92"
PETROL_95 = "petrol_95"
AUTO_DIESEL = "auto_diesel"
SUPER_DIESEL = "super_diesel"
KEROSENE = "kerosene"

ALL_FUELS = [PETROL_92, PETROL_95, AUTO_DIESEL, SUPER_DIESEL, KEROSENE]

DISPLAY = {
    PETROL_92: "Petrol 92 (Octane)",
    PETROL_95: "Petrol 95 (Super)",
    AUTO_DIESEL: "Auto Diesel",
    SUPER_DIESEL: "Super Diesel",
    KEROSENE: "Kerosene",
}

# CPC label aliases — used to normalize scraped table headers.
CPC_ALIASES: dict[str, str] = {
    # Current CPC table headers (as of 2026)
    "lp 95": PETROL_95,
    "lp 92": PETROL_92,
    "lad": AUTO_DIESEL,
    "lsd": SUPER_DIESEL,
    "lk": KEROSENE,
    # Legacy / long-form aliases
    "petrol 92 octane": PETROL_92,
    "petrol octane 92": PETROL_92,
    "octane 92": PETROL_92,
    "92 octane": PETROL_92,
    "petrol 92": PETROL_92,
    "petrol 95 octane": PETROL_95,
    "petrol octane 95": PETROL_95,
    "octane 95": PETROL_95,
    "95 octane": PETROL_95,
    "petrol 95": PETROL_95,
    "auto diesel": AUTO_DIESEL,
    "lanka auto diesel": AUTO_DIESEL,
    "super diesel": SUPER_DIESEL,
    "lanka super diesel": SUPER_DIESEL,
    "kerosene": KEROSENE,
    "lanka kerosene": KEROSENE,
}


def normalize(label: str) -> str | None:
    key = " ".join(label.lower().strip().split())
    if key in CPC_ALIASES:
        return CPC_ALIASES[key]
    for alias, fuel in CPC_ALIASES.items():
        if alias in key:
            return fuel
    return None

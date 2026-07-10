"""Canonical fuel-type identifiers used across scrapers and APIs."""

import re

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
    """Map a scraped label to a canonical fuel id.

    Short CPC codes (lp 92, lk, lad, …) must not match inside unrelated
    tokens like "LKR". Prefer longer aliases first.
    """
    key = " ".join(label.lower().strip().split())
    if key in CPC_ALIASES:
        return CPC_ALIASES[key]
    # Longer aliases first so "petrol 92 octane" wins over bare "92"-ish codes.
    for alias, fuel in sorted(CPC_ALIASES.items(), key=lambda item: -len(item[0])):
        if len(alias) <= 3:
            # Word-boundary match for short codes (lk, lad, lsd, …).
            if re.search(rf"(?<!\w){re.escape(alias)}(?!\w)", key):
                return fuel
        elif alias in key:
            return fuel
    return None

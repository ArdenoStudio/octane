"""Block disposable / throwaway inbox domains from alert and digest signup."""

from __future__ import annotations

DISPOSABLE_DOMAINS: frozenset[str] = frozenset(
    [
        "mailinator.com",
        "guerrillamail.com",
        "guerrillamail.org",
        "sharklasers.com",
        "yopmail.com",
        "tempmail.com",
        "temp-mail.org",
        "throwaway.email",
        "getnada.com",
        "trashmail.com",
        "dispostable.com",
        "maildrop.cc",
        "10minutemail.com",
        "10minutemail.net",
        "fakeinbox.com",
        "mohmal.com",
        "emailondeck.com",
        "spamgourmet.com",
        "mytrashmail.com",
        "mailnesia.com",
        "mailcatch.com",
        "anonbox.net",
        "armyspy.com",
        "cuvox.de",
        "dayrep.com",
        "einrot.com",
        "fleckens.hu",
        "gustr.com",
        "jourrapide.com",
        "rhyta.com",
        "superrito.com",
        "teleworm.us",
        "trash-mail.com",
    ]
)


def disposable_domain_blocked(email_domain: str) -> bool:
    d = email_domain.strip().lower()
    if not d:
        return False
    return d in DISPOSABLE_DOMAINS or any(d.endswith(f".{b}") for b in DISPOSABLE_DOMAINS)


def is_disposable_email(email: str) -> bool:
    parts = email.strip().lower().rsplit("@", 1)
    if len(parts) != 2 or not parts[0] or not parts[1]:
        return False
    return disposable_domain_blocked(parts[1])

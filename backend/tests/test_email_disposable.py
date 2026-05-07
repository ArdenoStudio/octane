import pytest

from app.email_disposable import disposable_domain_blocked, is_disposable_email


@pytest.mark.parametrize(
    "domain,expect",
    [
        ("mailinator.com", True),
        ("sub.mailinator.com", True),
        ("gmail.com", False),
        ("", False),
        ("EXAMPLE.COM", False),
    ],
)
def test_disposable_domain_blocked(domain: str, expect: bool) -> None:
    assert disposable_domain_blocked(domain) == expect


def test_is_disposable_email() -> None:
    assert is_disposable_email("a@mailinator.com") is True
    assert is_disposable_email("a@yopmail.com") is True
    assert is_disposable_email("good@gmail.com") is False
    assert is_disposable_email("notanemail") is False


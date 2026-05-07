"""Regression: importing the ASGI app must not fail schema wiring (SlowAPI + Pydantic v2)."""


def test_main_app_imports() -> None:
    from app.main import app

    assert app.title == "Octane API"

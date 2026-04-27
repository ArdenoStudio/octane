import httpx

from app.config import get_settings


def client(timeout: float = 30.0) -> httpx.Client:
    return httpx.Client(
        headers={"User-Agent": get_settings().scraper_user_agent},
        timeout=timeout,
        follow_redirects=True,
    )

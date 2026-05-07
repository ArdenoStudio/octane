from contextlib import contextmanager
from typing import Iterator

import psycopg
from psycopg.conninfo import make_conninfo
from psycopg.rows import dict_row

from app.config import get_settings

# Seconds (libpq) — Postgres must respond before accepting traffic on Fly or health checks hang.
_PG_CONNECT_TIMEOUT = 12


def _conninfo(database_url: str) -> str:
    return make_conninfo(database_url, connect_timeout=str(_PG_CONNECT_TIMEOUT))


@contextmanager
def connect() -> Iterator[psycopg.Connection]:
    settings = get_settings()
    conninfo = _conninfo(settings.database_url)
    with psycopg.connect(conninfo, row_factory=dict_row) as conn:
        yield conn


@contextmanager
def cursor() -> Iterator[psycopg.Cursor]:
    with connect() as conn:
        with conn.cursor() as cur:
            yield cur
            conn.commit()

from contextlib import contextmanager
from typing import Iterator

import psycopg
from psycopg.rows import dict_row

from app.config import get_settings


@contextmanager
def connect() -> Iterator[psycopg.Connection]:
    settings = get_settings()
    with psycopg.connect(settings.database_url, row_factory=dict_row) as conn:
        yield conn


@contextmanager
def cursor() -> Iterator[psycopg.Cursor]:
    with connect() as conn:
        with conn.cursor() as cur:
            yield cur
            conn.commit()

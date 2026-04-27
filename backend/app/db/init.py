"""Run as: python -m app.db.init"""
from pathlib import Path

from app.db.connection import cursor


def main() -> None:
    schema = Path(__file__).with_name("schema.sql").read_text()
    with cursor() as cur:
        cur.execute(schema)
    print("schema applied")


if __name__ == "__main__":
    main()

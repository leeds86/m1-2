"""Fetch real completed Upbit candles; optionally seed the configured store.

Run from backend: python -m scripts.import_data --market KRW-BTC --apply
Without --apply this makes only a public read request and prints a preview.
"""

import argparse
import json

from app.config import Settings
from app.providers import UpbitClient
from app.repositories import FirestoreStore, SQLiteStore
from app.routers.data import create_record
from app.schemas import ImportInput
from app.errors import AppError


def main():
    parser = argparse.ArgumentParser(description="Import up to 200 real, completed daily candles.")
    parser.add_argument("--market", default="KRW-BTC")
    parser.add_argument("--apply", action="store_true", help="Write to the configured data store.")
    args = parser.parse_args()
    market = ImportInput(market=args.market).market
    client = UpbitClient()
    try:
        rows = client.candles(market)
    finally:
        client.client.close()
    output = {"market": market, "count": len(rows), "first_date": rows[0]["date"] if rows else None,
              "last_date": rows[-1]["date"] if rows else None, "applied": False}
    if args.apply:
        settings = Settings.from_env()
        store = SQLiteStore(settings.sqlite_path) if settings.storage_backend == "sqlite" else FirestoreStore(settings)
        created = 0
        for row in rows:
            try:
                create_record(store, row, "upbit")
                created += 1
            except AppError as error:
                if error.status != 409:
                    raise
        output.update(applied=True, imported=created, skipped=len(rows) - created)
    print(json.dumps(output, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

import json
import os
from datetime import date, datetime

import psycopg2
import psycopg2.extras

SCHEMA = """
CREATE TABLE IF NOT EXISTS stg_listings (
    listing_id  TEXT        NOT NULL,
    run_id      TEXT        NOT NULL,
    raw         JSONB       NOT NULL,
    loaded_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (listing_id, run_id)
);
"""


def _json_serial(obj):
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    raise TypeError(f"Not serializable: {type(obj)}")


class PostgresPublisher:
    def __init__(self):
        dsn = os.getenv("DATABASE_URL")
        if dsn:
            self.conn = psycopg2.connect(dsn)
        else:
            self.conn = psycopg2.connect(
                host=os.getenv("DB_HOST"),
                port=int(os.getenv("DB_PORT", "5432")),
                dbname=os.getenv("DB_NAME"),
                user=os.getenv("DB_USER"),
                password=os.getenv("DB_PASSWORD"),
                sslmode="require",
            )

    def ensure_schema(self) -> None:
        with self.conn.cursor() as cur:
            cur.execute(SCHEMA)
        self.conn.commit()

    def insert_staging(self, cars: list[dict], run_id: str) -> None:
        self.ensure_schema()
        rows = [
            (
                car["id"],
                run_id,
                psycopg2.extras.Json(car, dumps=lambda o: json.dumps(o, default=_json_serial)),
            )
            for car in cars
            if car.get("id")
        ]
        with self.conn.cursor() as cur:
            psycopg2.extras.execute_values(
                cur,
                """
                INSERT INTO stg_listings (listing_id, run_id, raw)
                VALUES %s
                ON CONFLICT (listing_id, run_id) DO NOTHING
                """,
                rows,
            )
        self.conn.commit()
        print(f"Staged {len(rows)} listings (run_id={run_id})")

    def close(self) -> None:
        self.conn.close()

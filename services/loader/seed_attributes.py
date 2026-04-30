"""
One-time script: loads attributes.json into attribute_specs and attribute_spec_values.
Safe to re-run — uses upsert (ON CONFLICT DO NOTHING).

Usage:
    python seed_attributes.py path/to/attributes.json
"""

import json
import os
import sys

import psycopg2
import psycopg2.extras
from dotenv import load_dotenv

load_dotenv(override=False)

SCHEMA = """
CREATE TABLE IF NOT EXISTS attribute_specs (
    attribute_id         TEXT PRIMARY KEY,
    name                 TEXT NOT NULL,
    value_type           TEXT,
    hierarchy            TEXT,
    relevance            INT,
    attribute_group_id   TEXT,
    attribute_group_name TEXT
);

CREATE TABLE IF NOT EXISTS attribute_spec_values (
    value_id     TEXT NOT NULL,
    attribute_id TEXT NOT NULL REFERENCES attribute_specs(attribute_id),
    name         TEXT NOT NULL,
    PRIMARY KEY (value_id, attribute_id)
);
"""


def connect():
    return psycopg2.connect(os.environ["DATABASE_URL"])


def seed(path: str) -> None:
    with open(path, encoding="utf-8") as f:
        attributes: list[dict] = json.load(f)
        print(attributes)

    conn = connect()
    try:
        with conn.cursor() as cur:
            cur.execute(SCHEMA)

            attr_rows = [
                (
                    a["id"],
                    a.get("name", ""),
                    a.get("value_type"),
                    a.get("hierarchy"),
                    a.get("relevance"),
                    a.get("attribute_group_id"),
                    a.get("attribute_group_name"),
                )
                for a in attributes
            ]
            psycopg2.extras.execute_values(
                cur,
                """
                INSERT INTO attribute_specs
                    (attribute_id, name, value_type, hierarchy, relevance,
                     attribute_group_id, attribute_group_name)
                VALUES %s
                ON CONFLICT (attribute_id) DO NOTHING
                """,
                attr_rows,
            )
            print(f"Upserted {len(attr_rows)} attributes")

            value_rows = [
                (v["id"], a["id"], v.get("name", ""))
                for a in attributes
                for v in (a.get("values") or [])
                if "id" in v
            ]
            if value_rows:
                psycopg2.extras.execute_values(
                    cur,
                    """
                    INSERT INTO attribute_spec_values (value_id, attribute_id, name)
                    VALUES %s
                    ON CONFLICT (value_id, attribute_id) DO NOTHING
                    """,
                    value_rows,
                )
                print(f"Upserted {len(value_rows)} attribute values")

        conn.commit()
        print("Done.")
    finally:
        conn.close()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python seed_attributes.py <path-to-attributes.json>")
        sys.exit(1)
    seed(sys.argv[1])

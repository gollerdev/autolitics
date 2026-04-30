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

NORMALIZED_SCHEMA = """
CREATE TABLE IF NOT EXISTS norm_sellers (
    seller_id                  BIGINT      PRIMARY KEY,
    nickname                   TEXT,
    permalink                  TEXT,
    registration_date          TIMESTAMPTZ,
    car_dealer                 BOOLEAN,
    real_estate_agency         BOOLEAN,
    car_dealer_logo            TEXT,
    home_image_url             TEXT,
    rep_transactions_total     INT,
    rep_transactions_completed INT,
    rep_transactions_canceled  INT,
    rep_rating_positive        NUMERIC,
    rep_rating_negative        NUMERIC,
    rep_rating_neutral         NUMERIC,
    rep_sales_completed_365d   INT,
    tags                       TEXT[],
    updated_at                 TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS norm_listings (
    listing_id          TEXT        NOT NULL,
    run_id              TEXT        NOT NULL,
    extracted_at        TIMESTAMPTZ NOT NULL,
    site_id             TEXT,
    title               TEXT,
    price_usd           NUMERIC,
    currency_id         TEXT,
    condition           TEXT,
    permalink           TEXT,
    thumbnail           TEXT,
    thumbnail_id        TEXT,
    buying_mode         TEXT,
    listing_type_id     TEXT,
    category_id         TEXT,
    domain_id           TEXT,
    catalog_product_id  TEXT,
    stop_time           TIMESTAMPTZ,
    date_created        TIMESTAMPTZ,
    available_quantity  INT,
    sold_quantity       INT,
    accepts_mercadopago BOOLEAN,
    has_variations      BOOLEAN,
    seller_id           BIGINT,
    is_car_dealer       BOOLEAN,
    address_state_id    TEXT,
    address_state_name  TEXT,
    address_city_id     TEXT,
    address_city_name   TEXT,
    loc_city_id         TEXT,
    loc_city_name       TEXT,
    loc_state_id        TEXT,
    loc_state_name      TEXT,
    loc_country_id      TEXT,
    loc_country_name    TEXT,
    loc_latitude        NUMERIC,
    loc_longitude       NUMERIC,
    shipping_free       BOOLEAN,
    shipping_mode       TEXT,
    sale_price_amount   NUMERIC,
    sale_price_type     TEXT,
    brand               TEXT,
    model               TEXT,
    year                INT,
    kilometers          INT,
    fuel_type           TEXT,
    transmission        TEXT,
    color               TEXT,
    doors               INT,
    passenger_capacity  INT,
    engine              TEXT,
    displacement_cc     INT,
    power_hp            NUMERIC,
    traction            TEXT,
    has_ac              BOOLEAN,
    trim                TEXT,
    short_version       TEXT,
    loaded_at           TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (listing_id, run_id)
);

CREATE TABLE IF NOT EXISTS norm_listing_pictures (
    id           BIGSERIAL   PRIMARY KEY,
    listing_id   TEXT        NOT NULL,
    run_id       TEXT        NOT NULL,
    extracted_at TIMESTAMPTZ NOT NULL,
    picture_id   TEXT,
    url          TEXT
);

CREATE TABLE IF NOT EXISTS norm_listing_attributes (
    id                   BIGSERIAL   PRIMARY KEY,
    listing_id           TEXT        NOT NULL,
    run_id               TEXT        NOT NULL,
    extracted_at         TIMESTAMPTZ NOT NULL,
    attribute_id         TEXT,
    attribute_name       TEXT,
    value_id             TEXT,
    value_name           TEXT,
    attribute_group_id   TEXT,
    attribute_group_name TEXT,
    value_number         NUMERIC,
    value_unit           TEXT
);

CREATE TABLE IF NOT EXISTS norm_listing_sale_terms (
    id           BIGSERIAL   PRIMARY KEY,
    listing_id   TEXT        NOT NULL,
    run_id       TEXT        NOT NULL,
    extracted_at TIMESTAMPTZ NOT NULL,
    term_id      TEXT,
    term_name    TEXT,
    value_id     TEXT,
    value_name TEXT
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

    def ensure_normalized_schema(self) -> None:
        with self.conn.cursor() as cur:
            cur.execute(NORMALIZED_SCHEMA)
        self.conn.commit()

    def insert_normalized(self, cars: list[dict], run_id: str) -> None:
        from datetime import datetime
        from transformers.car_transformer import transform

        self.ensure_normalized_schema()

        extracted_at = datetime.strptime(run_id, "%Y%m%d_%H%M%S")

        seller_rows: list[tuple] = []
        listing_rows: list[tuple] = []
        picture_rows: list[tuple] = []
        attribute_rows: list[tuple] = []
        sale_term_rows: list[tuple] = []

        seen_seller_ids: set = set()

        for car in cars:
            if not car.get("id"):
                continue

            lid = car["id"]
            seller = car.get("seller") or {}
            seller_id = seller.get("id")

            if seller_id and seller_id not in seen_seller_ids:
                seen_seller_ids.add(seller_id)
                rep = seller.get("seller_reputation") or {}
                txn = rep.get("transactions") or {}
                ratings = txn.get("ratings") or {}
                metrics = rep.get("metrics") or {}
                sales = metrics.get("sales") or {}
                seller_rows.append((
                    seller_id,
                    seller.get("nickname"),
                    seller.get("permalink"),
                    seller.get("registration_date"),
                    seller.get("car_dealer"),
                    seller.get("real_estate_agency"),
                    seller.get("car_dealer_logo"),
                    seller.get("home_image_url"),
                    txn.get("total"),
                    txn.get("completed"),
                    txn.get("canceled"),
                    ratings.get("positive"),
                    ratings.get("negative"),
                    ratings.get("neutral"),
                    sales.get("completed"),
                    seller.get("tags") or [],
                ))

            flat = transform(car)
            addr = car.get("address") or {}
            loc  = car.get("location") or {}
            ship = car.get("shipping") or {}
            sp   = car.get("sale_price") or {}

            listing_rows.append((
                lid,
                run_id,
                extracted_at,
                car.get("site_id"),
                car.get("title"),
                car.get("price"),
                car.get("currency_id"),
                car.get("condition"),
                car.get("permalink"),
                car.get("thumbnail"),
                car.get("thumbnail_id"),
                car.get("buying_mode"),
                car.get("listing_type_id"),
                car.get("category_id"),
                car.get("domain_id"),
                car.get("catalog_product_id"),
                car.get("stop_time"),
                car.get("date_created"),
                car.get("available_quantity"),
                car.get("sold_quantity"),
                car.get("accepts_mercadopago"),
                car.get("has_variations"),
                seller_id,
                seller.get("car_dealer"),
                addr.get("state_id"),
                addr.get("state_name"),
                addr.get("city_id"),
                addr.get("city_name"),
                (loc.get("city") or {}).get("id"),
                (loc.get("city") or {}).get("name"),
                (loc.get("state") or {}).get("id"),
                (loc.get("state") or {}).get("name"),
                (loc.get("country") or {}).get("id"),
                (loc.get("country") or {}).get("name"),
                loc.get("latitude"),
                loc.get("longitude"),
                ship.get("free_shipping"),
                ship.get("mode"),
                sp.get("amount"),
                sp.get("type"),
                flat.get("brand"),
                flat.get("model"),
                flat.get("year"),
                flat.get("kilometers"),
                flat.get("fuel_type"),
                flat.get("transmission"),
                flat.get("color"),
                flat.get("doors"),
                flat.get("passenger_capacity"),
                flat.get("engine"),
                flat.get("displacement_cc"),
                flat.get("power_hp"),
                flat.get("traction"),
                flat.get("has_ac"),
                flat.get("trim"),
                flat.get("short_version"),
            ))

            for pic in car.get("pictures") or []:
                picture_rows.append((lid, run_id, extracted_at, pic.get("id"), pic.get("url")))

            for attr in car.get("attributes") or []:
                vs = (attr.get("value_struct") or {})
                attribute_rows.append((
                    lid,
                    run_id,
                    extracted_at,
                    attr.get("id"),
                    attr.get("name"),
                    attr.get("value_id"),
                    attr.get("value_name"),
                    attr.get("attribute_group_id"),
                    attr.get("attribute_group_name"),
                    vs.get("number"),
                    vs.get("unit"),
                ))

            for term in car.get("sale_terms") or []:
                sale_term_rows.append((
                    lid,
                    run_id,
                    extracted_at,
                    term.get("id"),
                    term.get("name"),
                    term.get("value_id"),
                    term.get("value_name"),
                ))

        with self.conn.cursor() as cur:
            if seller_rows:
                psycopg2.extras.execute_values(
                    cur,
                    """
                    INSERT INTO norm_sellers
                        (seller_id, nickname, permalink, registration_date,
                         car_dealer, real_estate_agency, car_dealer_logo, home_image_url,
                         rep_transactions_total, rep_transactions_completed, rep_transactions_canceled,
                         rep_rating_positive, rep_rating_negative, rep_rating_neutral,
                         rep_sales_completed_365d, tags)
                    VALUES %s
                    ON CONFLICT (seller_id) DO UPDATE SET
                        nickname = EXCLUDED.nickname,
                        permalink = EXCLUDED.permalink,
                        car_dealer = EXCLUDED.car_dealer,
                        tags = EXCLUDED.tags,
                        updated_at = NOW()
                    """,
                    seller_rows,
                )

            if listing_rows:
                psycopg2.extras.execute_values(
                    cur,
                    """
                    INSERT INTO norm_listings
                        (listing_id, run_id, extracted_at, site_id, title, price_usd, currency_id,
                         condition, permalink, thumbnail, thumbnail_id, buying_mode, listing_type_id,
                         category_id, domain_id, catalog_product_id, stop_time, date_created,
                         available_quantity, sold_quantity, accepts_mercadopago, has_variations,
                         seller_id, is_car_dealer,
                         address_state_id, address_state_name, address_city_id, address_city_name,
                         loc_city_id, loc_city_name, loc_state_id, loc_state_name,
                         loc_country_id, loc_country_name, loc_latitude, loc_longitude,
                         shipping_free, shipping_mode,
                         sale_price_amount, sale_price_type,
                         brand, model, year, kilometers, fuel_type, transmission, color,
                         doors, passenger_capacity, engine, displacement_cc, power_hp,
                         traction, has_ac, trim, short_version)
                    VALUES %s
                    ON CONFLICT (listing_id, run_id) DO NOTHING
                    """,
                    listing_rows,
                )

            if picture_rows:
                psycopg2.extras.execute_values(
                    cur,
                    "INSERT INTO norm_listing_pictures (listing_id, run_id, extracted_at, picture_id, url) VALUES %s",
                    picture_rows,
                )

            if attribute_rows:
                psycopg2.extras.execute_values(
                    cur,
                    """
                    INSERT INTO norm_listing_attributes
                        (listing_id, run_id, extracted_at, attribute_id, attribute_name,
                         value_id, value_name, attribute_group_id, attribute_group_name,
                         value_number, value_unit)
                    VALUES %s
                    """,
                    attribute_rows,
                )

            if sale_term_rows:
                psycopg2.extras.execute_values(
                    cur,
                    """
                    INSERT INTO norm_listing_sale_terms
                        (listing_id, run_id, extracted_at, term_id, term_name, value_id, value_name)
                    VALUES %s
                    """,
                    sale_term_rows,
                )

        self.conn.commit()
        print(
            f"Normalized: {len(listing_rows)} listings, {len(seller_rows)} norm_sellers upserted, "
            f"{len(picture_rows)} pictures, {len(attribute_rows)} attributes, "
            f"{len(sale_term_rows)} sale terms (run_id={run_id}, extracted_at={extracted_at})"
        )

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

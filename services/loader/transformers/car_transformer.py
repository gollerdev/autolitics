import re

# MercadoLibre attribute IDs → star-schema field names
ATTRIBUTE_MAP = {
    "BRAND":                "brand",
    "MODEL":                "model",
    "VEHICLE_YEAR":         "year",
    "KILOMETERS":           "kilometers",
    "FUEL_TYPE":            "fuel_type",
    "TRANSMISSION":         "transmission",
    "COLOR":                "color",
    "DOORS":                "doors",
    "PASSENGER_CAPACITY":   "passenger_capacity",
    "ENGINE":               "engine",
    "ENGINE_DISPLACEMENT":  "displacement_cc",
    "POWER":                "power_hp",
    "HAS_AIR_CONDITIONING": "has_ac",
    "TRIM":                 "trim",
    "SHORT_VERSION":        "short_version",
    # traction (drive type) has no MercadoLibre attribute — stays NULL
}

INT_FIELDS   = {"year", "kilometers", "doors", "passenger_capacity", "displacement_cc"}
FLOAT_FIELDS = {"power_hp"}
# Values that mean "yes" for boolean attributes (Spanish + English)
_YES = {"sí", "si", "yes", "true", "con aire"}


def _parse_int(value: str | None) -> int | None:
    if value is None:
        return None
    digits = re.sub(r"[^\d]", "", str(value))
    return int(digits) if digits else None


def _parse_float(value: str | None) -> float | None:
    if value is None:
        return None
    cleaned = re.sub(r"[^\d.]", "", str(value))
    try:
        return float(cleaned) if cleaned else None
    except ValueError:
        return None


def flatten_attributes(attributes: list[dict]) -> dict[str, dict]:
    """Convert the attributes list into a dict keyed by attribute id for easy lookup."""
    return {attr["id"]: attr for attr in (attributes or []) if "id" in attr}


def transform(car: dict) -> dict:
    """Transform a raw car dict (from Parquet) into a flat row ready for the star schema."""
    attrs = flatten_attributes(car.get("attributes") or [])

    row: dict = {
        "listing_id":         car.get("id"),
        "title":              car.get("title"),
        "price_usd":          car.get("price"),
        "currency_id":        car.get("currency_id"),
        "condition":          car.get("condition"),
        "permalink":          car.get("permalink"),
        "scraped_at":         car.get("date_created"),
        "city":               (car.get("address") or {}).get("city_name"),
        "state":              (car.get("address") or {}).get("state_name"),
        "seller_id":          (car.get("seller") or {}).get("id"),
        "seller_nickname":    (car.get("seller") or {}).get("nickname"),
        "is_car_dealer":      (car.get("seller") or {}).get("car_dealer", False),
        "brand":              None,
        "model":              None,
        "year":               None,
        "kilometers":         None,
        "fuel_type":          None,
        "transmission":       None,
        "color":              None,
        "doors":              None,
        "passenger_capacity": None,
        "engine":             None,
        "displacement_cc":    None,
        "power_hp":           None,
        "traction":           None,
        "has_ac":             None,
        "trim":               None,
        "short_version":      None,
    }

    for attr_id, field in ATTRIBUTE_MAP.items():
        attr = attrs.get(attr_id)
        if attr is None:
            continue
        value = attr.get("value_name")
        if field in INT_FIELDS:
            row[field] = _parse_int(value)
        elif field in FLOAT_FIELDS:
            row[field] = _parse_float(value)
        elif field == "has_ac":
            row[field] = value.strip().lower() in _YES if value else None
        else:
            row[field] = value

    return row

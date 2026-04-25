import json
import re
import os
import csv
import time
import random
from playwright.sync_api import sync_playwright

BASE_URL = "https://autos.mercadolibre.com.uy/_Desde_{offset}_PublishedToday_YES_NoIndex_True"


def is_blocked(html: str) -> bool:
    return "account-verification" in html or "gz-account-verification" in html


def extract_search_api(html: str) -> dict | None:
    match = re.search(r'<script id="__NORDIC_RENDERING_CTX__"[^>]*>(.*?)</script>', html, re.DOTALL)
    if not match:
        print("  No Nordic script tag found")
        return None
    raw = match.group(1).strip()
    parts = re.split(r'(?=_n\.)', raw)
    json_str = re.sub(r'^_n\.ctx\.r=', '', parts[1]).rstrip(';')
    data = json.loads(json_str)

    # Navigate to search_api recursively
    def find_key(obj, target, depth=0):
        if depth > 5:
            return None
        if isinstance(obj, dict):
            if target in obj:
                return obj[target]
            for v in obj.values():
                r = find_key(v, target, depth + 1)
                if r is not None:
                    return r
        return None

    return find_key(data, 'search_api')


def parse_car(item: dict) -> dict:
    # Build attribute lookup
    attrs = {a['id']: a.get('value_name', '') for a in item.get('attributes', [])}

    location = item.get('location', {})
    city = location.get('city', {}).get('name', '')
    state = location.get('state', {}).get('name', '')

    return {
        'id': item.get('id', ''),
        'title': item.get('title', ''),
        'price': item.get('price'),
        'currency': item.get('currency_id', ''),
        'condition': item.get('condition', ''),
        'date_created': item.get('date_created', ''),
        'permalink': item.get('permalink', ''),
        'thumbnail': item.get('thumbnail', ''),
        'city': city,
        'state': state,
        'seller_id': item.get('seller', {}).get('id', ''),
        'seller_name': item.get('seller', {}).get('nickname', ''),
        'is_car_dealer': item.get('seller', {}).get('car_dealer', False),
        'year': attrs.get('VEHICLE_YEAR', ''),
        'km': attrs.get('KILOMETERS', ''),
        'brand': attrs.get('BRAND', ''),
        'model': attrs.get('MODEL', ''),
        'version': attrs.get('VERSION', ''),
        'fuel': attrs.get('FUEL_TYPE', ''),
        'transmission': attrs.get('TRANSMISSION', ''),
        'color': attrs.get('COLOR', ''),
        'doors': attrs.get('DOORS', ''),
        'engine': attrs.get('ENGINE_DISPLACEMENT', ''),
    }


def fetch_offset(page, offset: int) -> list:
    url = BASE_URL.format(offset=offset)
    print(f"Fetching offset {offset}...")

    page.goto(url, wait_until="networkidle")
    html = page.content()

    if is_blocked(html):
        print(f"  Blocked! Waiting 30s and retrying...")
        time.sleep(30)
        page.goto(url, wait_until="networkidle")
        html = page.content()
        if is_blocked(html):
            print("  Still blocked. Skipping.")
            return []

    with open(f"debug_{offset}.html", "w", encoding="utf-8") as f:
        f.write(html)

    search_api = extract_search_api(html)
    if not search_api:
        print(f"  No search_api found at offset {offset}")
        return []

    results = search_api.get('results', [])
    total = search_api.get('paging', {}).get('total', '?')
    print(f"  Got {len(results)} listings (total available: {total})")

    return [parse_car(r) for r in results if r.get('type') == 'ITEM']


def scrape_all_cars(output_csv: str = "cars.csv"):
    all_cars = []

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=False,
            args=["--disable-blink-features=AutomationControlled"]
        )
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            viewport={"width": 1280, "height": 800},
            locale="es-UY",
            timezone_id="America/Montevideo",
        )
        context.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        page = context.new_page()

        # Warm up
        print("Warming up...")
        page.goto("https://autos.mercadolibre.com.uy/", wait_until="networkidle")
        time.sleep(random.uniform(3, 5))

        offset = 0
        while True:
            cars = fetch_offset(page, offset)

            if not cars:
                print(f"No results at offset {offset}, stopping.")
                break

            all_cars.extend(cars)
            offset += 48
            time.sleep(random.uniform(5, 10))

        browser.close()

    print(f"\nTotal cars scraped: {len(all_cars)}")

    if all_cars:
        with open(output_csv, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=all_cars[0].keys())
            writer.writeheader()
            writer.writerows(all_cars)
        print(f"Saved to {output_csv}")

    return all_cars


if __name__ == "__main__":
    scrape_all_cars("cars.csv")

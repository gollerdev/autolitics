import json
import re
import os
import time
import random
from playwright.sync_api import sync_playwright

BASE_URL = "https://autos.mercadolibre.com.uy/_Desde_{offset}_PublishedToday_YES_NoIndex_True"

def is_blocked(html: str) -> bool:
    return "account-verification" in html or "gz-account-verification" in html

def extract_data_from_html(html: str) -> dict | None:
    match = re.search(r'<script id="__NORDIC_RENDERING_CTX__"[^>]*>(.*?)</script>', html, re.DOTALL)
    if not match:
        print("No data found in page")
        return None
    raw = match.group(1).strip()
    parts = re.split(r'(?=_n\.)', raw)
    json_str = re.sub(r'^_n\.ctx\.r=', '', parts[1]).rstrip(';')
    return json.loads(json_str)

def fetch_offset(page, offset: int, output_dir: str = "api_responses") -> list:
    os.makedirs(output_dir, exist_ok=True)
    url = BASE_URL.format(offset=offset)
    print(f"Fetching offset {offset}...")

    api_data = {}

    def handle_response(response):
        if "PublishedToday" in response.url and response.request.resource_type == "document":
            return
        if "autos.mercadolibre.com.uy" in response.url and response.status == 200:
            try:
                body = response.json()
                api_data["data"] = body
            except Exception:
                pass

    page.on("response", handle_response)
    page.goto(url, wait_until="networkidle")
    page.remove_listener("response", handle_response)

    html = page.content()

    if is_blocked(html):
        print(f"⚠️  Blocked at offset {offset}! Waiting 30s before retrying...")
        time.sleep(30)
        page.goto(url, wait_until="networkidle")
        html = page.content()
        if is_blocked(html):
            print("Still blocked. Skipping this offset.")
            return []

    with open(f"debug_{offset}.html", "w", encoding="utf-8") as f:
        f.write(html)

    # Save API response if captured
    if "data" in api_data:
        out_path = os.path.join(output_dir, f"api_{offset}.json")
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(api_data["data"], f, ensure_ascii=False, indent=2)
        print(f"Saved API response to {out_path}")

    # Extract IDs from HTML
    data = extract_data_from_html(html)
    if not data:
        return []

    items = []
    try:
        header_components = data["appProps"]["pageProps"]["initialState"]["header_components"]
        for component in header_components:
            content = component.get("content", {})
            fast_loading = content.get("fast_loading", {})
            for item in fast_loading.get("items_pads_lite", []):
                items.append(item.get("id"))
    except (KeyError, TypeError):
        pass

    return items

def scrape_all_cars():
    all_ids = []

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=False,  # visible browser is much harder to detect
            args=["--disable-blink-features=AutomationControlled"]
        )
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            viewport={"width": 1280, "height": 800},
            locale="es-UY",
            timezone_id="America/Montevideo",
        )

        # Hide webdriver flag
        context.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")

        page = context.new_page()

        # Warm up: visit the homepage first like a real user would
        print("Warming up...")
        page.goto("https://autos.mercadolibre.com.uy/", wait_until="networkidle")
        time.sleep(random.uniform(3, 5))

        offset = 0
        while True:
            ids = fetch_offset(page, offset)

            if not ids:
                print(f"No more results at offset {offset}, stopping.")
                break

            print(f"Found {len(ids)} items at offset {offset}: {ids}")
            all_ids.extend(ids)
            offset += 48
            time.sleep(random.uniform(5, 10))

        browser.close()

    print(f"\nTotal car IDs found: {len(all_ids)}")
    with open("car_ids.txt", "w") as f:
        for car_id in all_ids:
            f.write(car_id + "\n")

    return all_ids

if __name__ == "__main__":
    scrape_all_cars()
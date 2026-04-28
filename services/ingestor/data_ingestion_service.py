import os
import re
import json
import time
import random
import datetime
from playwright.sync_api import sync_playwright
from storage_service.s3_storage_service import S3StorageService as StorageService
from queue_service.sqs_queue_service import SQSQueueService
from dotenv import load_dotenv
load_dotenv(override=False)
 
BASE_URL = "https://autos.mercadolibre.com.uy/_Desde_{offset}_PublishedToday_YES_NoIndex_True"
 
 
def is_blocked(html: str) -> bool:
    return "account-verification" in html or "gz-account-verification" in html
 
 
def get_total_listings(html: str) -> int | None:
    """Extract total listing count from the Nordic script tag."""
    match = re.search(r'<script id="__NORDIC_RENDERING_CTX__"[^>]*>(.*?)</script>', html, re.DOTALL)
    if not match:
        return None
    raw = match.group(1).strip()
    parts = re.split(r'(?=_n\.)', raw)
    json_str = re.sub(r'^_n\.ctx\.r=', '', parts[1]).rstrip(';')
    data = json.loads(json_str)
 
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
 
    search_api = find_key(data, 'search_api')
    if not search_api:
        return None
    return search_api.get('paging', {}).get('total')
 
 
def fetch_offset(page, offset: int, run_id: str, storage: StorageService) -> int | None:
    """Fetches a single page and delegates storage to the storage service.
    Returns total listings count on success, None on failure."""
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
            print("  Still blocked. Stopping.")
            return None
 
    total = get_total_listings(html)
    if total is None:
        print(f"  Could not determine total listings. Stopping.")
        return None
 
    print(f"  Total listings available: {total}")
 
    key = f"raw/{run_id}/offset_{offset}.html"
    saved_path = storage.save(key, html)
    print(f"  Saved to {saved_path}")
 
    return total
 
 
def run():
    run_id = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    started_at = datetime.datetime.utcnow().isoformat()
    storage = StorageService(base_path="data")
    queue = SQSQueueService()

    proxy_server = os.getenv("PROXY_SERVER")
    proxy = None
    if proxy_server:
        proxy = {
            "server": proxy_server,
            "username": os.getenv("PROXY_USERNAME"),
            "password": os.getenv("PROXY_PASSWORD"),
        }
        print(f"Using proxy: {proxy_server}")
    else:
        print("No proxy configured")
 
    print(f"Run ID: {run_id}")
 
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=False,
            args=["--disable-blink-features=AutomationControlled"]
        )
        context = browser.new_context(
            proxy=proxy,
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            viewport={"width": 1280, "height": 800},
            locale="es-UY",
            timezone_id="America/Montevideo",
        )
        context.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        page = context.new_page()
 
        # Warm up with homepage before hitting paginated URLs
        print("Warming up...")
        page.goto("https://autos.mercadolibre.com.uy/", wait_until="networkidle")
        time.sleep(random.uniform(4, 6))
 
        offset = 0
        pages_collected = 0
        offsets_collected = []
        extra_run_done = False
 
        while True:
            total = fetch_offset(page, offset, run_id, storage)
 
            if total is None:
                print(f"Stopping at offset {offset}.")
                break
 
            pages_collected += 1
            offsets_collected.append(offset)
            offset += 48
 
            if offset >= total:
                if extra_run_done:
                    print(f"Extra safety page collected. All done.")
                    break
                print(f"Reached end of listings (total: {total}). Fetching one extra page to be safe...")
                extra_run_done = True
 
            time.sleep(random.uniform(5, 10))
 
        browser.close()
 
    print(f"\nRun {run_id} complete. Pages collected: {pages_collected}")
 
    if pages_collected > 0:
        queue.publish({
            "run_id": run_id,
            "started_at": started_at,
            "finished_at": datetime.datetime.utcnow().isoformat(),
            "enqueued_at": datetime.datetime.utcnow().isoformat(),
            "pages_collected": pages_collected,
            "offsets": offsets_collected,
            "storage_backend": "s3",
            "bucket": os.getenv("S3_BUCKET"),
            "base_path": f"raw/{run_id}/",
            "source_url": "https://autos.mercadolibre.com.uy",
            "country": "UY",
        })
 
 
if __name__ == "__main__":
    run()
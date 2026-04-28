from playwright.sync_api import sync_playwright
from playwright_stealth import Stealth
from dotenv import load_dotenv
import random
import os

load_dotenv(override=False)

with sync_playwright() as p:
    browser = p.chromium.launch(
        headless=False,
        args=[
            "--disable-blink-features=AutomationControlled",
            "--ignore-certificate-errors",
        ]
    )

    context = browser.new_context(
        proxy={
            "server": os.getenv("PROXY_SERVER"),
            "username": os.getenv("PROXY_USERNAME"),
            "password": os.getenv("PROXY_PASSWORD"),
        },
        user_agent=(
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        ),
        viewport={"width": 1366, "height": 768},
        locale="es-UY",
        timezone_id="America/Montevideo",
    )

    stealth = Stealth()
    page = context.new_page()

    stealth.use_sync(page)

    page.goto("https://www.mercadolibre.com.", wait_until="domcontentloaded")

    page.wait_for_timeout(random.randint(1500, 3000))
    page.mouse.move(200, 300)
    page.mouse.wheel(0, random.randint(300, 800))
    page.wait_for_timeout(random.randint(1000, 2000))

    print("Final URL:", page.url)

    content = page.content()
    print(content[:2000])

    input("Press Enter to close...")
    browser.close()
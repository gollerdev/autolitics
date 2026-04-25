import httpx
from dotenv import load_dotenv
import os

load_dotenv()
CLIENT_ID = os.getenv("MERCADO_LIBRE_APP_ID")
API_KEY =  os.getenv("MERCADO_LIBRE_SECRET")
TOKEN = os.getenv("ACCESS_TOKEN")

SITE_ID = "MLU"

## This request handler was discarded as after doing some reserch I found out MELI does not allow to access car publications via their API.
def get_token():
    "Get token to use Mercado Libre API, unfortunately this process cannot be automated thus this function is deprecated and does not work. token will have to be manually set in dotenv file"
    url = f"https://auth.mercadolibre.com.uy/authorization?response_type=code&client_id={CLIENT_ID}&redirect_uri=https://github.com/gollerdev"

    with httpx.Client() as client:
        response = client.get(url)
        response.raise_for_status()
        data = response.json()
    return data

def create_test_user():
    url = "https://api.mercadolibre.com/users/test_user"

    headers = {
        "Authorization": f"Bearer {TOKEN}",
        "Content-type": "application/json"
    }

    body = {
        "site_id": SITE_ID
    }

    with httpx.Client() as client:
        response = client.post(url, headers=headers, json=body)
        print(f"Status: {response.status_code}")
        print(f"Response: {response.text}")
        response.raise_for_status()
        return response.json()

def get_todays_car_catalog_call():
    url = f"https://api.mercadolibre.com/sites/{SITE_ID}/search"
    
    params = {
        "domain_id": "MLU-VEHICLES",
        "sort": "start_time_desc",
        "limit": "50",

    }
    
    headers = {
        "Authorization": f"Bearer {TOKEN}"
    }
    
    with httpx.Client() as client:
        response = client.get(url, headers=headers, params=params)
        response.raise_for_status()
        data = response.json()
    
    today = date.today().isoformat()
    todays_cars = [
        item for item in data.get("results", [])
        if item.get("start_time", "").startswith(today)
    ]
    
    return todays_cars

def search_products(query: str, status: str = "active"):
    url = "https://api.mercadolibre.com/products/search"

    headers = {
        "Authorization": f"Bearer {TOKEN}"
    }

    params = {
        "site_id": SITE_ID,
        "status": status,
        "q": query,
        "limit": "100",
    }

    with httpx.Client() as client:
        response = client.get(url, headers=headers, params=params)
        print(f"Status: {response.status_code}")
        response.raise_for_status()
        data = response.json()

    results = data.get("results", [])
    print(f"Found {len(results)} products for query: '{query}'")
    for product in results:
        print(f"  - {product['domain_id']} | {product['id']} | {product['name']} | status: {product['status']}")

    return data

if __name__ == "__main__":
    data = search_products("Baw L7 100 Eléctrico 0km 2026 Retira U$d 7.990 Y Financia")
    
    with open("results.txt", "w", encoding="utf-8") as f:
        import json
        json.dump(data, f, ensure_ascii=False, indent=4)
    
    print("Results saved to results.txt")
import httpx
from dotenv import load_dotenv
import os

load_dotenv()

CLIENT_ID = os.getenv("MERCADO_LIBRE_APP_ID")
CLIENT_SECRET = os.getenv("MERCADO_LIBRE_SECRET")
CODE = os.getenv("STABLE_TOKEN")
REDIRECT_URI = os.getenv("CALLBACK_URI")

def exchange_code_for_token():
    url = "https://api.mercadolibre.com/oauth/token"

    headers = {
        "accept": "application/json",
        "content-type": "application/x-www-form-urlencoded",
    }

    data = {
        "grant_type": "authorization_code",
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "code": CODE,
        "redirect_uri": REDIRECT_URI,
    }

    with httpx.Client() as client:
        response = client.post(url, headers=headers, data=data)
        response.raise_for_status()
        return response.json()

if __name__ == "__main__":
    print(CLIENT_ID)
    print(CLIENT_SECRET)
    print(CODE)
    print(REDIRECT_URI)
    tokens = exchange_code_for_token()
    print(tokens)
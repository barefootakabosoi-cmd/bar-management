import requests
from config import Config

def get_token():
    url = "https://online.sbis.ru/oauth/service/"
    payload = {
        "app_client_id": Config.SBIS_CLIENT_ID,
        "app_secret": Config.SBIS_APP_SECRET,
        "secret_key": Config.SBIS_SECRET_KEY
    }
    resp = requests.post(url, json=payload, headers={"Content-Type": "application/json"}, timeout=30)
    return resp.json().get("token")

token = get_token()
headers = {"X-SBISAccessToken": token}

endpoints = [
    "https://api.sbis.ru/retail/warehouse/list",
    "https://api.sbis.ru/retail/stock/list",
    "https://api.sbis.ru/retail/nomenclature/balances",
    "https://api.sbis.ru/retail/v2/nomenclature/balances",
]

for url in endpoints:
    print(f"\n=== {url} ===")
    resp = requests.get(url, headers=headers, timeout=30)
    print(f"Status: {resp.status_code}")
    if resp.status_code == 200:
        data = resp.json()
        print(f"Data: {str(data)[:200]}")
    else:
        print(f"Error: {resp.text[:100]}")


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
if not token:
    print("No token!")
    exit()

headers = {"X-SBISAccessToken": token}

# Получаем точки с прайс-листами
url = "https://api.sbis.ru/retail/point/list?withPrices=true&pageSize=10"
resp = requests.get(url, headers=headers, timeout=30)
print(f"Status: {resp.status_code}")
if resp.status_code == 200:
    data = resp.json()
    points = data.get('salesPoints', [])
    for p in points:
        print(f"\nID: {p.get('id')}")
        print(f"Name: {p.get('name')}")
        print(f"Product: {p.get('product')}")
        print(f"Prices: {p.get('prices', [])}")
        print(f"DefaultPriceList: {p.get('defaultPriceList')}")
        print(f"DefaultPriceLists: {p.get('defaultPriceLists', [])}")


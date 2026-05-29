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

configs = [
    ("265", "39"),
    ("265", None),
    ("259", None),
    ("259", "39"),
]

for point, price in configs:
    print(f"\n=== pointId={point}, priceListId={price} ===")
    url = "https://api.sbis.ru/retail/v2/nomenclature/list"
    params = {"pointId": point, "withBalance": "true", "pageSize": "5"}
    if price:
        params["priceListId"] = price
    
    resp = requests.get(url, headers=headers, params=params, timeout=30)
    print(f"Status: {resp.status_code}")
    if resp.status_code == 200:
        data = resp.json()
        items = data if isinstance(data, list) else data.get('items', [])
        print(f"Items: {len(items)}")
        for item in items[:2]:
            print(f"  {item.get('name')} - balance: {item.get('balance')}")


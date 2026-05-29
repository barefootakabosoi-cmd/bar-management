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
point_id = "265"
price_list_id = "39"

urls = [
    f"https://api.sbis.ru/retail/v2/nomenclature/list?pointId={point_id}&priceListId={price_list_id}&withBalance=true&pageSize=5",
    f"https://api.sbis.ru/retail/nomenclature/list?pointId={point_id}&priceListId={price_list_id}&withBalance=true&pageSize=5",
    f"https://online.sbis.ru/retail/v2/nomenclature/list?pointId={point_id}&priceListId={price_list_id}&withBalance=true&pageSize=5",
    f"https://online.sbis.ru/retail/nomenclature/list?pointId={point_id}&priceListId={price_list_id}&withBalance=true&pageSize=5",
]

for url in urls:
    print(f"\n=== {url} ===")
    resp = requests.get(url, headers=headers, timeout=30)
    print(f"Status: {resp.status_code}")
    if resp.status_code == 200:
        data = resp.json()
        items = data if isinstance(data, list) else data.get('items', [])
        print(f"Items: {len(items)}")
        for item in items[:2]:
            print(f"  ID: {item.get('id')}, Name: {item.get('name')}, Balance: {item.get('balance')}")
    else:
        print(f"Error: {resp.text[:100]}")


import requests
import json

config = {}
with open('.env', 'r') as f:
    for line in f:
        if '=' in line and not line.startswith('#'):
            key, val = line.strip().split('=', 1)
            config[key] = val

url = "https://online.sbis.ru/oauth/service/"
payload = {
    "app_client_id": config.get('SBIS_CLIENT_ID'),
    "app_secret": config.get('SBIS_APP_SECRET'),
    "secret_key": config.get('SBIS_SECRET_KEY')
}
resp = requests.post(url, json=payload, headers={"Content-Type": "application/json"}, timeout=30)
token = resp.json().get("token")
print(f"Token: {token[:20]}..." if token else f"Auth error: {resp.json()}")

if not token:
    exit()

headers = {"X-SBISAccessToken": token}
point_id = config.get('SBIS_POINT_ID', '265')

endpoints = [
    f"https://api.sbis.ru/retail/v2/nomenclature/list?pointId={point_id}&withBalance=true&pageSize=5",
    f"https://api.sbis.ru/retail/nomenclature/list?pointId={point_id}&withBalance=true&pageSize=5",
    f"https://api.sbis.ru/retail/nomenclature/balances?pointId={point_id}&pageSize=5",
]

for url in endpoints:
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
        print(f"Error: {resp.text[:200]}")

print(f"\n=== SALES ===")
url = f"https://api.sbis.ru/retail/order/list?pointId={point_id}&page=0&pageSize=5"
resp = requests.get(url, headers=headers, timeout=30)
print(f"Status: {resp.status_code}")
if resp.status_code == 200:
    data = resp.json()
    orders = data.get('orders', []) if isinstance(data, dict) else []
    print(f"Orders: {len(orders)}")
    for order in orders[:2]:
        print(f"  ID: {order.get('id')}, Sum: {order.get('sum')}, Date: {order.get('date')}")
else:
    print(f"Error: {resp.text[:200]}")

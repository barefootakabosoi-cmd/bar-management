import requests
from config import Config

def get_oauth_token():
    url = "https://online.sbis.ru/oauth/service/"
    payload = {
        "app_client_id": Config.SBIS_CLIENT_ID,
        "app_secret": Config.SBIS_APP_SECRET,
        "secret_key": Config.SBIS_SECRET_KEY
    }
    resp = requests.post(url, json=payload, headers={"Content-Type": "application/json"}, timeout=30)
    data = resp.json()
    token = data.get("token")
    print(f"Token: {token[:20]}..." if token else f"Auth error: {data}")
    return token

def test_retail_api():
    token = get_oauth_token()
    if not token:
        return
    
    headers = {"X-SBISAccessToken": token}
    
    # 1. Получаем точки продаж
    print("\n=== SALES POINTS ===")
    url = "https://api.sbis.ru/retail/point/list"
    resp = requests.get(url, headers=headers, timeout=30)
    print(f"Status: {resp.status_code}")
    if resp.status_code == 200:
        data = resp.json()
        points = data.get('salesPoints', [])
        print(f"Points: {len(points)}")
        for p in points[:3]:
            print(f"  ID: {p.get('id')}, Name: {p.get('name')}, Product: {p.get('product')}")
    
    # 2. Получаем остатки (нужен pointId)
    print("\n=== BALANCES ===")
    point_id = Config.SBIS_POINT_ID
    if not point_id:
        print("No SBIS_POINT_ID in config")
        return
    
    url = f"https://api.sbis.ru/retail/v2/nomenclature/list?pointId={point_id}&withBalance=true&pageSize=10"
    resp = requests.get(url, headers=headers, timeout=30)
    print(f"Status: {resp.status_code}")
    if resp.status_code == 200:
        data = resp.json()
        items = data if isinstance(data, list) else data.get('items', [])
        print(f"Items: {len(items)}")
        for item in items[:3]:
            print(f"  ID: {item.get('id')}, Name: {item.get('name')}, Balance: {item.get('balance')}")
    else:
        print(f"Error: {resp.text[:200]}")
    
    # 3. Получаем продажи (orders)
    print("\n=== SALES ===")
    url = f"https://api.sbis.ru/retail/order/list?pointId={point_id}&page=0&pageSize=10"
    resp = requests.get(url, headers=headers, timeout=30)
    print(f"Status: {resp.status_code}")
    if resp.status_code == 200:
        data = resp.json()
        orders = data.get('orders', []) if isinstance(data, dict) else []
        print(f"Orders: {len(orders)}")
        for order in orders[:3]:
            print(f"  ID: {order.get('id')}, Sum: {order.get('sum')}, Date: {order.get('date')}")
    else:
        print(f"Error: {resp.text[:200]}")

if __name__ == "__main__":
    test_retail_api()

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
    return resp.json().get("token")

def get_doc_details(doc_id):
    token = get_oauth_token()
    headers = {
        "Content-Type": "application/json-rpc;charset=utf-8",
        "Accept": "application/json",
        "X-SBISAccessToken": token
    }
    
    url = "https://online.sbis.ru/service/?srv=1"
    payload = {
        "jsonrpc": "2.0",
        "method": "СБИС.ПрочитатьДокумент",
        "params": {
            "Документ": {
                "Идентификатор": doc_id
            }
        },
        "id": 1
    }
    
    resp = requests.post(url, json=payload, headers=headers, timeout=30)
    return resp.json()

data = get_doc_details("УНПРОС26-081384")
print("Keys:", list(data.keys()))
if "result" in data:
    result = data["result"]
    print("Result keys:", list(result.keys()))
    print("Номер:", result.get("Номер"))
    print("Дата:", result.get("Дата"))
    print("Сумма:", result.get("Сумма"))
    print("Контрагент:", result.get("Контрагент", {}).get("Название"))
    print("Вложения:", len(result.get("Вложение", [])))
    
    # Проверим товары
    for key in ["Товары", "Номенклатура", "Наименования", "Состав"]:
        if key in result:
            items = result[key]
            print(f"\n{key}: {len(items) if isinstance(items, list) else 'not list'}")
            if isinstance(items, list) and items:
                print(f"  Example: {items[0]}")
else:
    print("Error:", data.get("error"))

import requests
from config import Config
from datetime import datetime, timedelta

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

headers = {
    "Content-Type": "application/json-rpc;charset=utf-8",
    "Accept": "application/json",
    "X-SBISAccessToken": token
}

date_from = (datetime.now() - timedelta(days=7)).strftime("%d.%m.%Y")
date_to = datetime.now().strftime("%d.%m.%Y")

doc_types = ["ДокОтгрИсх", "ДокОтгрВх", "Реализация", "Чек"]

for doc_type in doc_types:
    print(f"\n=== {doc_type} ===")
    url = "https://online.sbis.ru/service/?srv=1"
    payload = {
        "jsonrpc": "2.0",
        "method": "СБИС.СписокДокументов",
        "params": {
            "Фильтр": {
                "Тип": doc_type,
                "ДатаС": date_from,
                "ДатаПо": date_to,
                "Навигация": {
                    "РазмерСтраницы": "10",
                    "Страница": "1"
                }
            }
        },
        "id": 1
    }
    
    resp = requests.post(url, json=payload, headers=headers, timeout=30)
    print(f"Status: {resp.status_code}")
    if resp.status_code == 200:
        data = resp.json()
        if "result" in data:
            result = data["result"]
            docs = result.get("Документ", []) if isinstance(result, dict) else []
            print(f"Docs: {len(docs)}")
            if docs:
                print(f"Example: {docs[0].get('Номер')} - {docs[0].get('Сумма')} - {docs[0].get('Контрагент', {}).get('Название', 'N/A')}")
        elif "error" in data:
            print(f"Error: {data['error']}")


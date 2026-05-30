from sbis_retail_api import SbisRetailAPI
from config import Config
import requests
import json

sbis = SbisRetailAPI(
    token=Config.SBIS_TOKEN,
    client_id=Config.SBIS_CLIENT_ID,
    app_secret=Config.SBIS_APP_SECRET,
    secret_key=Config.SBIS_SECRET_KEY
)
sbis.authenticate()

url = 'https://online.sbis.ru/service/?srv=1'
headers = {
    'X-SBISAccessToken': sbis.token,
    'Content-Type': 'application/json'
}

def get_docs(doc_type, limit=3):
    payload = {
        'jsonrpc': '2.0',
        'method': 'СБИС.СписокДокументов',
        'params': {
            'Фильтр': {
                'Тип': doc_type,
                'Период': {'Начало': '01.05.2026', 'Конец': '31.05.2026'}
            }
        },
        'id': 1
    }
    resp = requests.post(url, headers=headers, json=payload, timeout=30)
    return resp.json()

def read_doc(doc_id, doc_type):
    payload = {
        'jsonrpc': '2.0',
        'method': 'СБИС.ПрочитатьДокумент',
        'params': {
            'Документ': {
                'Идентификатор': doc_id,
                'Тип': doc_type
            }
        },
        'id': 1
    }
    resp = requests.post(url, headers=headers, json=payload, timeout=30)
    return resp.json()

# === ДОКОТГРИСХ (РОЗНИЧНЫЕ ПРОДАЖИ) ===
print("=" * 60)
print("ДОКОТГРИСХ")
print("=" * 60)
r = get_docs('ДокОтгрИсх')
if 'result' in r:
    for d in r['result'].get('Документ', [])[:2]:
        print(f"\n--- {d.get('Номер')} от {d.get('Дата')} ---")
        print(f"ID: {d.get('Идентификатор')}")
        print(f"Примечание: {d.get('Примечание', '')}")
        print(f"Сумма: {d.get('Сумма', '')}")
        
        full = read_doc(d['Идентификатор'], 'ДокОтгрИсх')
        if 'result' in full:
            data = full['result']
            print(f"Ключи: {list(data.keys())}")
            if 'Расширение' in data:
                print(f"Расширение: {json.dumps(data['Расширение'], ensure_ascii=False, indent=2)[:800]}")
            if 'Наименования' in data:
                print(f"\n>>> НАИМЕНОВАНИЯ НАЙДЕНЫ!")
                for item in data['Наименования'][:3]:
                    print(f"    {item.get('Номенклатура','')}: {item.get('Количество','')} x {item.get('Цена','')} = {item.get('Сумма','')}")
            if 'ТаблДок' in data:
                print(f"\n>>> ТАБЛДОК НАЙДЕН!")
                for item in data['ТаблДок'][:3]:
                    print(f"    {item}")

# === АКТСПИСАНИЯ ===
print("\n" + "=" * 60)
print("АКТСПИСАНИЯ")
print("=" * 60)
r = get_docs('АктСписания')
if 'result' in r:
    for d in r['result'].get('Документ', [])[:2]:
        print(f"\n--- {d.get('Номер')} от {d.get('Дата')} ---")
        print(f"ID: {d.get('Идентификатор')}")
        print(f"Примечание: {d.get('Примечание', '')}")
        print(f"Сумма: {d.get('Сумма', '')}")
        
        full = read_doc(d['Идентификатор'], 'АктСписания')
        if 'result' in full:
            data = full['result']
            print(f"Ключи: {list(data.keys())}")
            if 'Расширение' in data:
                print(f"Расширение: {json.dumps(data['Расширение'], ensure_ascii=False, indent=2)[:800]}")
            if 'Наименования' in data:
                print(f"\n>>> НАИМЕНОВАНИЯ:")
                for item in data['Наименования'][:3]:
                    print(f"    {item.get('Номенклатура','')}: {item.get('Количество','')} x {item.get('Цена','')}")

# === ВНУТРПРМ ===
print("\n" + "=" * 60)
print("ВНУТРПРМ (всего 1 документ!)")
print("=" * 60)
r = get_docs('ВнутрПрм')
if 'result' in r:
    for d in r['result'].get('Документ', []):
        print(f"\n--- {d.get('Номер')} от {d.get('Дата')} ---")
        print(f"ID: {d.get('Идентификатор')}")
        print(f"Примечание: {d.get('Примечание', '')}")
        print(f"Сумма: {d.get('Сумма', '')}")
        
        full = read_doc(d['Идентификатор'], 'ВнутрПрм')
        if 'result' in full:
            data = full['result']
            print(f"Ключи: {list(data.keys())}")
            print(f"ПОЛНЫЙ ДОКУМЕНТ:")
            print(json.dumps(data, ensure_ascii=False, indent=2)[:3000])

# === КАССОВЫЙДЕНЬ ===
print("\n" + "=" * 60)
print("КАССОВЫЙДЕНЬ")
print("=" * 60)
r = get_docs('КассовыйДень')
if 'result' in r:
    for d in r['result'].get('Документ', [])[:2]:
        print(f"\n--- {d.get('Номер')} от {d.get('Дата')} ---")
        print(f"ID: {d.get('Идентификатор')}")
        print(f"Примечание: {d.get('Примечание', '')}")
        print(f"Сумма: {d.get('Сумма', '')}")
        
        full = read_doc(d['Идентификатор'], 'КассовыйДень')
        if 'result' in full:
            data = full['result']
            print(f"Ключи: {list(data.keys())}")
            if 'Расширение' in data:
                print(f"Расширение: {json.dumps(data['Расширение'], ensure_ascii=False, indent=2)[:1000]}")


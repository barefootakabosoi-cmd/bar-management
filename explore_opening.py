from sbis_retail_api import SbisRetailAPI
from config import Config
import requests
import json
import xml.etree.ElementTree as ET

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

def download_file(file_url):
    try:
        file_headers = {'X-SBISAccessToken': sbis.token}
        resp = requests.get(file_url, headers=file_headers, timeout=30)
        return resp
    except Exception as e:
        print(f"Ошибка: {e}")
        return None

# === 1. Проверим DocOpening ===
print("=" * 60)
print("DOCOPENING - ПРОВЕРКА ДОСТУПНОСТИ")
print("=" * 60)

payload = {
    'jsonrpc': '2.0',
    'method': 'СБИС.СписокДокументов',
    'params': {
        'Фильтр': {
            'Тип': 'DocOpening',
            'Период': {'Начало': '01.05.2026', 'Конец': '31.05.2026'}
        }
    },
    'id': 1
}
resp = requests.post(url, headers=headers, json=payload, timeout=30)
result = resp.json()

if 'error' in result:
    print(f"ОШИБКА: {result['error']}")
else:
    docs = result.get('result', {}).get('Документ', [])
    print(f"DocOpening: {len(docs)} документов")
    for d in docs:
        print(f"\n--- DocOpening {d.get('Номер')} от {d.get('Дата')} ---")
        print(f"ID: {d.get('Идентификатор')}")
        print(f"Примечание: {d.get('Примечание', '')}")
        print(f"Сумма: {d.get('Сумма', '')}")
        
        full = read_doc(d['Идентификатор'], 'DocOpening')
        if 'result' in full:
            data = full['result']
            print(f"Ключи: {list(data.keys())}")
            
            if 'Расширение' in data:
                print(f"Расширение: {json.dumps(data['Расширение'], ensure_ascii=False, indent=2)[:800]}")
            
            if 'ВложениеУчета' in data and len(data['ВложениеУчета']) > 0:
                v = data['ВложениеУчета'][0]
                if 'Файл' in v and 'Ссылка' in v['Файл']:
                    print(f"\nСкачиваем XML...")
                    file_resp = download_file(v['Файл']['Ссылка'])
                    if file_resp and file_resp.status_code == 200:
                        xml_text = file_resp.text
                        print(f"XML ({len(xml_text)} символов):")
                        print(xml_text[:3000])
                        
                        try:
                            root = ET.fromstring(xml_text)
                            print(f"\n=== Парсинг XML ===")
                            for elem in root.iter():
                                tag = elem.tag.split('}')[-1] if '}' in elem.tag else elem.tag
                                if any(x in tag for x in ['Номенклатура', 'Товар', 'Наименование', 'Количество', 'Цена', 'Кег', 'AlcCode', 'ГТИН']):
                                    if elem.text and len(elem.text) > 1:
                                        print(f"  {tag}: {elem.text}")
                        except Exception as e:
                            print(f"Ошибка парсинга: {e}")
                    else:
                        status = file_resp.status_code if file_resp else 'None'
                        print(f"Ошибка: {status}")

# === 2. Проверим СменаККМ ===
print("\n" + "=" * 60)
print("СМЕНАККМ - ПРОВЕРКА")
print("=" * 60)

payload = {
    'jsonrpc': '2.0',
    'method': 'СБИС.СписокДокументов',
    'params': {
        'Фильтр': {
            'Тип': 'СменаККМ',
            'Период': {'Начало': '25.05.2026', 'Конец': '31.05.2026'}
        }
    },
    'id': 1
}
resp = requests.post(url, headers=headers, json=payload, timeout=30)
result = resp.json()

if 'error' in result:
    print(f"ОШИБКА: {result['error']}")
else:
    docs = result.get('result', {}).get('Документ', [])
    print(f"СменаККМ: {len(docs)} документов")
    for d in docs[:3]:
        print(f"  {d.get('Номер')} от {d.get('Дата')} - {d.get('Примечание', '')}")

# === 3. Проверим другие возможные типы ===
print("\n" + "=" * 60)
print("ДРУГИЕ ТИПЫ ДОКУМЕНТОВ")
print("=" * 60)

other_types = ['DocOpening', 'Смена', 'СменаККМ', 'КассоваяСмена', 'ЧекККМ', 'Чек', 'ОтчетОПродажах']
for t in other_types:
    payload = {
        'jsonrpc': '2.0',
        'method': 'СБИС.СписокДокументов',
        'params': {
            'Фильтр': {
                'Тип': t,
                'Период': {'Начало': '25.05.2026', 'Конец': '31.05.2026'}
            }
        },
        'id': 1
    }
    resp = requests.post(url, headers=headers, json=payload, timeout=30)
    result = resp.json()
    if 'error' in result:
        err = result.get('error', {})
        msg = err.get('message', 'Unknown')
        if 'неизвестный' in msg.lower() or 'unknown' in msg.lower():
            print(f"{t}: НЕИЗВЕСТНЫЙ ТИП")
        else:
            print(f"{t}: ОШИБКА - {msg}")
    else:
        docs = result.get('result', {}).get('Документ', [])
        print(f"{t}: {len(docs)} документов")

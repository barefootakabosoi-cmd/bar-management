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
        print(f"Ошибка скачивания: {e}")
        return None

# === АКТСПИСАНИЯ - скачиваем XML ===
print("=" * 60)
print("АКТСПИСАНИЯ - СКАЧИВАНИЕ XML")
print("=" * 60)

payload = {
    'jsonrpc': '2.0',
    'method': 'СБИС.СписокДокументов',
    'params': {
        'Фильтр': {
            'Тип': 'АктСписания',
            'Период': {'Начало': '28.05.2026', 'Конец': '31.05.2026'}
        }
    },
    'id': 1
}
resp = requests.post(url, headers=headers, json=payload, timeout=30)
result = resp.json()

if 'result' in result and result['result'].get('Документ'):
    for d in result['result']['Документ'][:5]:
        doc_id = d['Идентификатор']
        print(f"\n--- {d.get('Номер')} от {d.get('Дата')} ---")
        print(f"Примечание: {d.get('Примечание', '')}")
        
        full = read_doc(doc_id, 'АктСписания')
        if 'result' in full:
            data = full['result']
            
            if 'ДокументОснование' in data:
                print(f"ДокументОснование:")
                for item in data['ДокументОснование']:
                    doc = item.get('Документ', {})
                    print(f"  → {doc.get('Тип')} {doc.get('Номер')} от {doc.get('Дата')}")
            
            if 'ВложениеУчета' in data and len(data['ВложениеУчета']) > 0:
                v = data['ВложениеУчета'][0]
                if 'Файл' in v and 'Ссылка' in v['Файл']:
                    file_url = v['Файл']['Ссылка']
                    print(f"\nСкачиваем XML...")
                    file_resp = download_file(file_url)
                    if file_resp and file_resp.status_code == 200:
                        xml_text = file_resp.text
                        print(f"XML получен ({len(xml_text)} символов)")
                        print(f"\n=== XML (первые 3000 символов) ===")
                        print(xml_text[:3000])
                        
                        try:
                            root = ET.fromstring(xml_text)
                            print(f"\n=== Корневой тег: {root.tag} ===")
                            for elem in root.iter():
                                if any(x in elem.tag for x in ['Номенклатура', 'Товар', 'Наименование', 'Количество', 'Цена']):
                                    if elem.text and len(elem.text) > 1:
                                        print(f"  {elem.tag.split('}')[-1]}: {elem.text}")
                        except Exception as e:
                            print(f"Ошибка парсинга: {e}")
                    else:
                        status = file_resp.status_code if file_resp else 'None'
                        print(f"Ошибка скачивания: {status}")
                        if file_resp:
                            print(file_resp.text[:500])

# === ДОКОТГРИСХ - ВложениеУчета ===
print("\n" + "=" * 60)
print("ДОКОТГРИСХ - ВЛОЖЕНИЕУЧЕТА")
print("=" * 60)

payload = {
    'jsonrpc': '2.0',
    'method': 'СБИС.СписокДокументов',
    'params': {
        'Фильтр': {
            'Тип': 'ДокОтгрИсх',
            'Период': {'Начало': '25.05.2026', 'Конец': '31.05.2026'}
        }
    },
    'id': 1
}
resp = requests.post(url, headers=headers, json=payload, timeout=30)
result = resp.json()

if 'result' in result and result['result'].get('Документ'):
    for d in result['result']['Документ'][:2]:
        doc_id = d['Идентификатор']
        print(f"\n--- {d.get('Номер')} от {d.get('Дата')} ---")
        
        full = read_doc(doc_id, 'ДокОтгрИсх')
        if 'result' in full:
            data = full['result']
            
            if 'ВложениеУчета' in data and len(data['ВложениеУчета']) > 0:
                v = data['ВложениеУчета'][0]
                print(f"ВложениеУчета ключи: {list(v.keys())}")
                if 'Файл' in v and 'Ссылка' in v['Файл']:
                    file_url = v['Файл']['Ссылка']
                    print(f"\nСкачиваем XML...")
                    file_resp = download_file(file_url)
                    if file_resp and file_resp.status_code == 200:
                        print(f"XML ({len(file_resp.text)} символов):")
                        print(file_resp.text[:3000])
                    else:
                        status = file_resp.status_code if file_resp else 'None'
                        print(f"Ошибка: {status}")

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

def parse_xml_items(xml_text):
    items = []
    try:
        root = ET.fromstring(xml_text)
        for doc in root.iter('Документ'):
            for tabl_tovar in doc.iter('ТаблТовар'):
                for str_tabl in tabl_tovar.iter('СтрТабл'):
                    item = {
                        'Наименование': str_tabl.get('Наименование', ''),
                        'Количество': str_tabl.get('Количество', ''),
                        'ЕдИзм': str_tabl.get('ЕдИзм', ''),
                        'Цена': str_tabl.get('Цена', ''),
                        'Сумма': str_tabl.get('Сумма', ''),
                        'НомНомер': str_tabl.get('НомНомер', ''),
                        'ГТИН': str_tabl.get('ГТИН', ''),
                    }
                    for param in str_tabl.iter('Параметр'):
                        if param.get('Имя') == 'AlcCode':
                            item['AlcCode'] = param.get('Значение', '')
                    items.append(item)
    except Exception as e:
        print(f"Ошибка парсинга: {e}")
    return items

# === DOCOPENING ===
print("=" * 60)
print("DOCOPENING - ВСКРЫТИЕ КЕГИ")
print("=" * 60)

payload = {
    'jsonrpc': '2.0',
    'method': 'СБИС.СписокДокументов',
    'params': {
        'Фильтр': {
            'Тип': 'DocOpening',
            'Период': {'Начало': '25.05.2026', 'Конец': '31.05.2026'}
        }
    },
    'id': 1
}
resp = requests.post(url, headers=headers, json=payload, timeout=30)
result = resp.json()

if 'result' in result and result['result'].get('Документ'):
    for d in result['result']['Документ'][:5]:
        doc_id = d['Идентификатор']
        print(f"\n--- DocOpening {d.get('Номер')} от {d.get('Дата')} ---")
        print(f"ID: {doc_id}")
        print(f"Сумма: {d.get('Сумма', '')}")
        
        full = read_doc(doc_id, 'DocOpening')
        if 'result' in full:
            data = full['result']
            
            if 'ДокументСледствие' in data:
                print(f"ДокументСледствие:")
                for item in data['ДокументСледствие']:
                    doc = item.get('Документ', {})
                    print(f"  → {doc.get('Тип')} {doc.get('Номер')} от {doc.get('Дата')}")
            
            if 'ВложениеУчета' in data and len(data['ВложениеУчета']) > 0:
                v = data['ВложениеУчета'][0]
                if 'Файл' in v and 'Ссылка' in v['Файл']:
                    file_resp = download_file(v['Файл']['Ссылка'])
                    if file_resp and file_resp.status_code == 200:
                        items = parse_xml_items(file_resp.text)
                        print(f"Товары ({len(items)} позиций):")
                        for item in items:
                            print(f"  • {item['Наименование']}")
                            print(f"    Кол-во: {item['Количество']} {item['ЕдИзм']}, Цена: {item['Цена']}₽, AlcCode: {item.get('AlcCode', 'N/A')}")
                    else:
                        status = file_resp.status_code if file_resp else 'None'
                        print(f"Ошибка: {status}")

# === ДОКОТГРИСХ ===
print("\n" + "=" * 60)
print("ДОКОТГРИСХ - РОЗНИЧНЫЕ ПРОДАЖИ")
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
    for d in result['result']['Документ'][:3]:
        doc_id = d['Идентификатор']
        print(f"\n--- ДокОтгрИсх {d.get('Номер')} от {d.get('Дата')} ---")
        print(f"Сумма: {d.get('Сумма', '')}")
        
        full = read_doc(doc_id, 'ДокОтгрИсх')
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
                    file_resp = download_file(v['Файл']['Ссылка'])
                    if file_resp and file_resp.status_code == 200:
                        items = []
                        try:
                            root = ET.fromstring(file_resp.text)
                            for doc in root.iter('Документ'):
                                for tabl in doc.iter('ТаблСчФакт'):
                                    for sv in tabl.iter('СведТов'):
                                        items.append({
                                            'Наименование': sv.get('НаимТов', ''),
                                            'Количество': sv.get('КолТов', ''),
                                            'ЕдИзм': sv.get('НаимЕдИзм', ''),
                                            'Цена': sv.get('ЦенаТов', ''),
                                            'Сумма': sv.get('СтТовБезНДС', ''),
                                        })
                        except Exception as e:
                            print(f"Ошибка: {e}")
                        
                        print(f"Товары ({len(items)} позиций):")
                        for item in items[:10]:
                            print(f"  • {item['Наименование']}")
                            print(f"    Кол-во: {item['Количество']} {item['ЕдИзм']}, Цена: {item['Цена']}₽")
                    else:
                        status = file_resp.status_code if file_resp else 'None'
                        print(f"Ошибка: {status}")

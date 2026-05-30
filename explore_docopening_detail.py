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

# === DOCOPENING - детальное изучение ===
print("=" * 60)
print("DOCOPENING - ДЕТАЛЬНОЕ ИЗУЧЕНИЕ")
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
    for d in result['result']['Документ'][:3]:
        doc_id = d['Идентификатор']
        print(f"\n{'='*50}")
        print(f"DocOpening {d.get('Номер')} от {d.get('Дата')}")
        print(f"Сумма: {d.get('Сумма', '')}")

        full = read_doc(doc_id, 'DocOpening')
        if 'result' in full:
            data = full['result']
            print(f"Ключи: {list(data.keys())}")

            if 'Вложение' in data:
                print(f"\nВложение ({len(data['Вложение'])} шт):")
                for i, v in enumerate(data['Вложение']):
                    print(f"  [{i}] Название: {v.get('Название')}, Подтип: {v.get('Подтип')}")
                    if v.get('СсылкаНаHTML'):
                        try:
                            html_resp = requests.get(v['СсылкаНаHTML'], headers={'X-SBISAccessToken': sbis.token}, timeout=30)
                            print(f"      HTML: {html_resp.status_code}")
                            if html_resp.status_code == 200:
                                print(html_resp.text[:1500])
                        except Exception as e:
                            print(f"      Ошибка: {e}")

            if 'ВложениеУчета' in data:
                print(f"\nВложениеУчета ({len(data['ВложениеУчета'])} шт):")
                for v in data['ВложениеУчета']:
                    print(f"  {json.dumps(v, ensure_ascii=False, indent=2)[:500]}")

            if 'Расширение' in data:
                print(f"\nРасширение: {json.dumps(data['Расширение'], ensure_ascii=False, indent=2)}")

# === АКТСПИСАНИЯ (следствие DocOpening) ===
print("\n" + "=" * 60)
print("АКТСПИСАНИЯ - НОМЕНКЛАТУРА")
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
        if d.get('Номер') in ['412', '411', '407', '406']:
            doc_id = d['Идентификатор']
            print(f"\n--- АктСписания {d.get('Номер')} от {d.get('Дата')} ---")
            print(f"Примечание: {d.get('Примечание', '')}")

            full = read_doc(doc_id, 'АктСписания')
            if 'result' in full:
                data = full['result']

                if 'ДокументОснование' in data:
                    print(f"Основание:")
                    for item in data['ДокументОснование']:
                        doc = item.get('Документ', {})
                        print(f"  → {doc.get('Тип')} {doc.get('Номер')}")

                if 'ВложениеУчета' in data and len(data['ВложениеУчета']) > 0:
                    v = data['ВложениеУчета'][0]
                    if 'Файл' in v and 'Ссылка' in v['Файл']:
                        file_resp = download_file(v['Файл']['Ссылка'])
                        if file_resp and file_resp.status_code == 200:
                            xml_text = file_resp.text
                            print(f"\nXML ({len(xml_text)} символов):")
                            print(xml_text[:2000])

                            try:
                                root = ET.fromstring(xml_text)
                                for doc in root.iter('Документ'):
                                    for tabl in doc.iter('ТаблТовар'):
                                        for str_tabl in tabl.iter('СтрТабл'):
                                            name = str_tabl.get('Наименование', '')
                                            qty = str_tabl.get('Количество', '')
                                            unit = str_tabl.get('ЕдИзм', '')
                                            price = str_tabl.get('Цена', '')
                                            print(f"\n  → {name}")
                                            print(f"    {qty} {unit} x {price}₽")
                            except Exception as e:
                                print(f"Ошибка: {e}")

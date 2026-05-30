from sbis_retail_api import SbisRetailAPI
from config import Config
import requests
import json
import zipfile
import io

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

# === 1. ДОКОТГРИСХ - архив с токеном ===
print("=" * 60)
print("ДОКОТГРИСХ - АРХИВ С ТОКЕНОМ")
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
    d = result['result']['Документ'][0]
    doc_id = d['Идентификатор']
    print(f"\nДокумент: {d.get('Номер')} от {d.get('Дата')}")
    
    full = read_doc(doc_id, 'ДокОтгрИсх')
    if 'result' in full:
        data = full['result']
        
        # Пробуем СсылкаНаАрхив с токеном
        if 'СсылкаНаАрхив' in data:
            archive_url = data['СсылкаНаАрхив']
            print(f"СсылкаНаАрхив: {archive_url[:120]}...")
            
            # Скачиваем с токеном
            try:
                archive_headers = {
                    'X-SBISAccessToken': sbis.token,
                    'Cookie': f'sbisToken={sbis.token}'
                }
                archive_resp = requests.get(archive_url, headers=archive_headers, timeout=30)
                print(f"Статус: {archive_resp.status_code}")
                
                if archive_resp.status_code == 200:
                    content_type = archive_resp.headers.get('Content-Type', '')
                    print(f"Content-Type: {content_type}")
                    print(f"Размер: {len(archive_resp.content)} bytes")
                    
                    # Пробуем ZIP
                    try:
                        z = zipfile.ZipFile(io.BytesIO(archive_resp.content))
                        print(f"Файлы: {z.namelist()}")
                        for name in z.namelist():
                            if name.endswith('.xml'):
                                xml = z.read(name).decode('utf-8')
                                print(f"\n=== {name} ===")
                                print(xml[:3000])
                    except zipfile.BadZipFile:
                        print("Не ZIP. Первые 2000 символов:")
                        print(archive_resp.text[:2000])
                else:
                    print(f"Ошибка: {archive_resp.status_code}")
                    print(archive_resp.text[:500])
            except Exception as e:
                print(f"Ошибка: {e}")
        
        # Пробуем Вложение
        print(f"\n--- Вложение ---")
        if 'Вложение' in data:
            for v in data['Вложение'][:3]:
                print(f"  Название: {v.get('Название')}")
                print(f"  Подтип: {v.get('Подтип')}")
                print(f"  СсылкаНаHTML: {v.get('СсылкаНаHTML', '')[:100]}...")
                print(f"  СсылкаНаPDF: {v.get('СсылкаНаPDF', '')[:100]}...")
                print()

# === 2. АКТСПИСАНИЯ - смотрим Вложение ===
print("\n" + "=" * 60)
print("АКТСПИСАНИЯ - ВЛОЖЕНИЕ")
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
    for d in result['result']['Документ'][:3]:
        doc_id = d['Идентификатор']
        print(f"\n--- {d.get('Номер')} от {d.get('Дата')} ---")
        print(f"Примечание: {d.get('Примечание', '')}")
        
        full = read_doc(doc_id, 'АктСписания')
        if 'result' in full:
            data = full['result']
            
            # Вложение
            if 'Вложение' in data:
                print(f"Вложение ({len(data['Вложение'])} шт):")
                for v in data['Вложение'][:2]:
                    print(f"  Название: {v.get('Название')}")
                    print(f"  Подтип: {v.get('Подтип')}")
                    print(f"  СсылкаНаHTML: {v.get('СсылкаНаHTML', '')[:80]}...")
                    
                    # Попробуем скачать HTML
                    if v.get('СсылкаНаHTML'):
                        try:
                            html_resp = requests.get(v['СсылкаНаHTML'], headers={'X-SBISAccessToken': sbis.token}, timeout=30)
                            print(f"  HTML статус: {html_resp.status_code}")
                            if html_resp.status_code == 200:
                                print(f"  HTML первые 1000 символов:")
                                print(html_resp.text[:1000])
                        except Exception as e:
                            print(f"  HTML ошибка: {e}")
            
            # ВложениеУчета
            if 'ВложениеУчета' in data:
                print(f"ВложениеУчета: {json.dumps(data['ВложениеУчета'], ensure_ascii=False, indent=2)[:1000]}")
            
            # ДокументОснование
            if 'ДокументОснование' in data:
                print(f"ДокументОснование: {json.dumps(data['ДокументОснование'], ensure_ascii=False)[:500]}")

# === 3. Проверим ДокОтгрВх (поступления) для сравнения ===
print("\n" + "=" * 60)
print("ДОКОТГРВХ - СРАВНЕНИЕ (поступление от поставщика)")
print("=" * 60)

payload = {
    'jsonrpc': '2.0',
    'method': 'СБИС.СписокДокументов',
    'params': {
        'Фильтр': {
            'Тип': 'ДокОтгрВх',
            'Период': {'Начало': '25.05.2026', 'Конец': '31.05.2026'}
        }
    },
    'id': 1
}
resp = requests.post(url, headers=headers, json=payload, timeout=30)
result = resp.json()

if 'result' in result and result['result'].get('Документ'):
    d = result['result']['Документ'][0]
    print(f"\nДокумент: {d.get('Номер')} от {d.get('Дата')}")
    
    full = read_doc(d['Идентификатор'], 'ДокОтгрВх')
    if 'result' in full:
        data = full['result']
        print(f"Ключи: {list(data.keys())}")
        
        if 'Наименования' in data:
            print(f"\n>>> Наименования найдены ({len(data['Наименования'])} позиций):")
            for item in data['Наименования'][:5]:
                print(f"    {item.get('Номенклатура','')}: {item.get('Количество','')} x {item.get('Цена','')} = {item.get('Сумма','')}")
        
        if 'СсылкаНаАрхив' in data:
            print(f"\nСсылкаНаАрхив: {data['СсылкаНаАрхив'][:100]}...")

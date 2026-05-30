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

# === 1. ДОКОТГРИСХ - скачаем архив ===
print("=" * 60)
print("ДОКОТГРИСХ - СКАЧИВАНИЕ АРХИВА (SR2D)")
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
    print(f"ID: {doc_id}")
    
    full = read_doc(doc_id, 'ДокОтгрИсх')
    if 'result' in full:
        data = full['result']
        
        if 'СсылкаНаАрхив' in data:
            archive_url = data['СсылкаНаАрхив']
            print(f"\nСсылкаНаАрхив: {archive_url[:100]}...")
            
            try:
                archive_resp = requests.get(archive_url, timeout=30)
                print(f"Статус: {archive_resp.status_code}")
                
                if archive_resp.status_code == 200:
                    try:
                        z = zipfile.ZipFile(io.BytesIO(archive_resp.content))
                        print(f"Файлы в архиве: {z.namelist()}")
                        
                        for name in z.namelist():
                            if name.endswith('.xml'):
                                xml_content = z.read(name).decode('utf-8')
                                print(f"\n=== {name} ===")
                                print(xml_content[:3000])
                    except zipfile.BadZipFile:
                        print("Не ZIP. Текст:")
                        print(archive_resp.text[:2000])
                else:
                    print(f"Ошибка: {archive_resp.status_code}")
                    print(archive_resp.text[:500])
            except Exception as e:
                print(f"Ошибка: {e}")

# === 2. АКТСПИСАНИЯ - номенклатура ===
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
    for d in result['result']['Документ'][:3]:
        doc_id = d['Идентификатор']
        print(f"\n--- {d.get('Номер')} от {d.get('Дата')} ---")
        print(f"Примечание: {d.get('Примечание', '')}")
        
        full = read_doc(doc_id, 'АктСписания')
        if 'result' in full:
            data = full['result']
            print(f"Ключи: {list(data.keys())}")
            
            if 'Наименования' in data:
                print(f">>> Наименования:")
                for item in data['Наименования'][:5]:
                    print(f"    {json.dumps(item, ensure_ascii=False)}")
            
            if 'ТаблДок' in data:
                print(f">>> ТаблДок:")
                for item in data['ТаблДок'][:5]:
                    print(f"    {json.dumps(item, ensure_ascii=False)}")
            
            if 'Расширение' in data:
                ext = data['Расширение']
                print(f"Расширение ключи: {list(ext.keys())}")
                for k, v in ext.items():
                    if isinstance(v, list) and len(v) > 0 and isinstance(v[0], dict):
                        if any(key in v[0] for key in ['Номенклатура', 'Товар', 'Наименование']):
                            print(f">>> Найдена номенклатура в Расширение.{k}:")
                            for item in v[:3]:
                                print(f"    {json.dumps(item, ensure_ascii=False)}")
            
            if 'СсылкаНаАрхив' in data:
                print(f"\nПробуем скачать архив...")
                try:
                    archive_resp = requests.get(data['СсылкаНаАрхив'], timeout=30)
                    if archive_resp.status_code == 200:
                        try:
                            z = zipfile.ZipFile(io.BytesIO(archive_resp.content))
                            for name in z.namelist():
                                if name.endswith('.xml'):
                                    xml = z.read(name).decode('utf-8')
                                    print(f"\n=== {name} ===")
                                    print(xml[:2000])
                        except:
                            print(archive_resp.text[:1000])
                except Exception as e:
                    print(f"Ошибка: {e}")

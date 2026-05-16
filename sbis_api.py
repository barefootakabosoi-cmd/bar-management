import requests
import xml.etree.ElementTree as ET
import json
import os
from datetime import datetime, timedelta
from urllib.parse import unquote

class Config:
    SBIS_CLIENT_ID = os.environ.get('SBIS_CLIENT_ID', '')
    SBIS_APP_SECRET = os.environ.get('SBIS_APP_SECRET', '')
    SBIS_SECRET_KEY = os.environ.get('SBIS_SECRET_KEY', '')
    SBIS_TOKEN = os.environ.get('SBIS_TOKEN', '')

class SbisAPI:
    def __init__(self, token=None, client_id=None, app_secret=None, secret_key=None):
        self.token = token or Config.SBIS_TOKEN
        self.client_id = client_id or Config.SBIS_CLIENT_ID
        self.app_secret = app_secret or Config.SBIS_APP_SECRET
        self.secret_key = secret_key or Config.SBIS_SECRET_KEY
        self.base_url = "https://online.sbis.ru"
        self.api_url = "https://online.sbis.ru"
        self.headers = {
            "Content-Type": "application/json-rpc;charset=utf-8",
            "Accept": "application/json"
        }

    def authenticate(self):
        """Public auth method for app.py"""
        return self._get_oauth_token()

    def _get_oauth_token(self):
        """Сервисная OAuth авторизация"""
        url = f"{self.base_url}/oauth/service/"
        payload = {
            "app_client_id": self.client_id,
            "app_secret": self.app_secret,
            "secret_key": self.secret_key
        }
        try:
            resp = requests.post(url, json=payload, headers={"Content-Type": "application/json"}, timeout=30)
            print(f"OAuth response: {resp.status_code}")
            if resp.status_code == 200:
                data = resp.json()
                if "token" in data:
                    self.token = data["token"]
                    self.headers["X-SBISAccessToken"] = self.token
                    print("Authenticated successfully")
                    return True
                elif "error" in data:
                    print(f"Auth error: {data['error']}")
                    return False
            else:
                print(f"Auth failed: {resp.status_code}")
                return False
        except Exception as e:
            print(f"Auth exception: {e}")
            return False

    def get_documents(self, doc_type="ДокОтгрВх", days_back=7):
        """Список документов СБИС"""
        if not self.token:
            if not self._get_oauth_token():
                return []

        date_from = (datetime.now() - timedelta(days=days_back)).strftime("%d.%m.%Y")
        date_to = datetime.now().strftime("%d.%m.%Y")

        url = f"{self.api_url}/service/?srv=1"
        payload = {
            "jsonrpc": "2.0",
            "method": "СБИС.СписокДокументов",
            "params": {
                "Фильтр": {
                    "Тип": doc_type,
                    "ДатаС": date_from,
                    "ДатаПо": date_to
                }
            },
            "id": 1
        }

        try:
            resp = requests.post(url, json=payload, headers=self.headers, timeout=60)
            print(f"List docs response: {resp.status_code}")
            if resp.status_code == 200:
                data = resp.json()
                if "result" in data:
                    result = data["result"]
                    docs = result.get("Документ", []) if isinstance(result, dict) else []
                    print(f"Found {len(docs)} documents")
                    return docs
                elif "error" in data:
                    print(f"API error: {data['error']}")
                    return []
            else:
                print(f"Request failed: {resp.status_code}")
                return []
        except Exception as e:
            print(f"Request exception: {e}")
            return []

    def sync_documents(self, date_from, date_to, existing_doc_ids=None):
        """Sync documents from SBIS (compatible with app.py)"""
        if existing_doc_ids is None:
            existing_doc_ids = set()
        
        days_back = (datetime.now() - date_from).days + 1
        
        result = {'new': [], 'updated': [], 'errors': []}
        
        docs = self.get_documents("ДокОтгрВх", days_back)
        
        for doc_summary in docs:
            doc_id = doc_summary.get("Идентификатор", "")
            if not doc_id:
                continue
            
            if doc_id in existing_doc_ids:
                continue
            
            details = self.get_document_details(doc_id)
            if details:
                result['new'].append(details)
            else:
                result['errors'].append(doc_id)
        
        return result

    def get_document_details(self, doc_id):
        """Получить детали документа"""
        if not self.token:
            if not self._get_oauth_token():
                return None

        url = f"{self.api_url}/service/?srv=1"
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

        try:
            resp = requests.post(url, json=payload, headers=self.headers, timeout=60)
            if resp.status_code == 200:
                data = resp.json()
                if "result" in data:
                    return data["result"]
            return None
        except Exception as e:
            print(f"Details error: {e}")
            return None


    def _safe_float(self, val):
        if val is None:
            return 0.0
        try:
            return float(str(val).replace(",", ".").replace(" ", ""))
        except:
            return 0.0

    def _parse_upd_items(self, xml_data):
        """Парсинг УПД 5.03 — данные в атрибутах СведТов"""
        items = []
        try:
            root = None
            for enc in ["utf-8", "windows-1251", "cp1251"]:
                try:
                    root = ET.fromstring(xml_data.decode(enc))
                    break
                except:
                    continue
            if not root:
                return items
            
            for elem in root.iter():
                tag = elem.tag.split("}")[-1] if "}" in elem.tag else elem.tag
                if tag == "СведТов":
                    attr = elem.attrib
                    if "НаимТов" in attr:
                        items.append({
                            "name": attr.get("НаимТов", ""),
                            "quantity": self._safe_float(attr.get("КолТов", "0")),
                            "price": self._safe_float(attr.get("ЦенаТов", "0")),
                            "sum": self._safe_float(attr.get("СтТовУчНал", attr.get("СтТовБезНДС", "0"))),
                            "unit": attr.get("НаимЕдИзм", "шт"),
                            "vat_rate": attr.get("НалСт", "")
                        })
        except Exception as e:
            print(f"ERROR parse XML: {e}")
        return items

    def _download_file(self, url):
        """Скачать файл с авторизацией СБИС"""
        try:
            headers = {"X-SBISAccessToken": self.token}
            resp = requests.get(url, headers=headers, timeout=60, allow_redirects=True)
            resp.raise_for_status()
            return resp.content
        except Exception as e:
            print(f"ERROR download: {e}")
            return None

    def get_items_from_upd(self, doc_meta):
        """Получить номенклатуру из XML УПД документа"""
        items = []
        attachments = doc_meta.get("Вложение", [])
        
        for att in attachments:
            if att.get("Тип") in ["УпдСчфДоп", "УпдДоп", "СчетФактура", "Торг12"]:
                file_info = att.get("Файл", {})
                file_url = file_info.get("Ссылка", "")
                if not file_url:
                    continue
                
                print(f"Downloading UPD: {file_info.get('Имя', '')[:60]}")
                xml_data = self._download_file(file_url)
                if not xml_data:
                    continue
                
                file_items = self._parse_upd_items(xml_data)
                items.extend(file_items)
                print(f"  Items found: {len(file_items)}")
        
        return items

    def get_sr2d_items(self, doc_id):
        """SR2D через ДокОтгрВх.SR2D"""
        if not self.token:
            if not self._get_oauth_token():
                return []

        url = f"{self.api_url}/service/?srv=1"
        payload = {
            "jsonrpc": "2.0",
            "method": "ДокОтгрВх.SR2D",
            "params": {
                "Идентификатор": doc_id
            },
            "id": 1
        }

        try:
            resp = requests.post(url, json=payload, headers=self.headers, timeout=60)
            print(f"SR2D response for {doc_id}: {resp.status_code}")
            if resp.status_code == 200:
                data = resp.json()
                if "result" in data:
                    result = data["result"]
                    items = result.get("Товары") or result.get("Наименования") or []
                    return items if items else []
            return []
        except Exception as e:
            print(f"SR2D error: {e}")
            return []

    def sync_all_documents(self, doc_type="ДокОтгрВх", days_back=7):
        """Полная синхронизация документов"""
        docs = self.get_documents(doc_type, days_back)
        results = []
        for doc in docs:
            doc_id = doc.get("Идентификатор", "")
            if not doc_id:
                continue
            details = self.get_document_details(doc_id)
            if details:
                results.append({
                    "id": doc_id,
                    "number": doc.get("Номер", ""),
                    "date": doc.get("Дата", ""),
                    "supplier": doc.get("Контрагент", {}).get("Название", ""),
                    "total": doc.get("Сумма", 0),
                    "details": details
                })
        return results


# ─── Helper functions for Flask app ───

def create_sbis_api_from_config(config):
    """Create SbisAPI instance from Flask config"""
    return SbisAPI(
        token=config.get('SBIS_TOKEN', ''),
        client_id=config.get('SBIS_CLIENT_ID', ''),
        app_secret=config.get('SBIS_APP_SECRET', ''),
        secret_key=config.get('SBIS_SECRET_KEY', '')
    )


def get_last_sync_date(db_model):
    """Get date of last successful sync"""
    return datetime.utcnow() - timedelta(days=365)

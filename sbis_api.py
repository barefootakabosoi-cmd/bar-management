import requests
import xml.etree.ElementTree as ET
import json
import os
from datetime import datetime, timedelta


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
        self.retail_url = "https://api.sbis.ru"
        self.headers = {
            "Content-Type": "application/json-rpc;charset=utf-8",
            "Accept": "application/json"
        }

    def authenticate(self):
        url = f"{self.base_url}/oauth/service/"
        payload = {
            "app_client_id": self.client_id,
            "app_secret": self.app_secret,
            "secret_key": self.secret_key
        }
        try:
            resp = requests.post(url, json=payload, headers={"Content-Type": "application/json"}, timeout=30)
            if resp.status_code == 200:
                data = resp.json()
                if "token" in data:
                    self.token = data["token"]
                    self.headers["X-SBISAccessToken"] = self.token
                    return True
                elif "access_token" in data:
                    self.token = data["access_token"]
                    self.headers["X-SBISAccessToken"] = self.token
                    return True
            print(f"Auth failed: {resp.status_code}, {resp.text[:200]}")
            return False
        except Exception as e:
            print(f"Auth exception: {e}")
            return False

    def _ensure_auth(self):
        if not self.token:
            return self.authenticate()
        return True

    def _rpc_call(self, method, params, retry=True):
        if not self._ensure_auth():
            return None
        url = f"{self.base_url}/service/?srv=1"
        payload = {"jsonrpc": "2.0", "method": method, "params": params, "id": 1}
        try:
            resp = requests.post(url, json=payload, headers=self.headers, timeout=60)
            if resp.status_code == 200:
                return resp.json().get("result")
            elif resp.status_code in (401, 403) and retry:
                if self.authenticate():
                    return self._rpc_call(method, params, retry=False)
            print(f"RPC {method} error: {resp.status_code}")
            return None
        except Exception as e:
            print(f"RPC {method} exception: {e}")
            return None

    def get_documents(self, doc_type="ДокОтгрВх", date_from=None, date_to=None, page_size=50):
        if date_from is None:
            date_from = (datetime.now() - timedelta(days=7)).strftime("%d.%m.%Y")
        elif isinstance(date_from, datetime):
            date_from = date_from.strftime("%d.%m.%Y")

        if date_to is None:
            date_to = datetime.now().strftime("%d.%m.%Y")
        elif isinstance(date_to, datetime):
            date_to = date_to.strftime("%d.%m.%Y")

        all_docs = []
        page = 1
        while True:
            result = self._rpc_call("СБИС.СписокДокументов", {
                "Фильтр": {
                    "Тип": doc_type,
                    "ДатаС": date_from,
                    "ДатаПо": date_to,
                    "Навигация": {"РазмерСтраницы": str(page_size), "Страница": str(page)}
                }
            })
            if not result:
                break
            docs = result.get("Документ", []) if isinstance(result, dict) else []
            all_docs.extend(docs)
            nav = result.get("Навигация", {}) if isinstance(result, dict) else {}
            has_more = nav.get("ЕстьЕще", "Нет") == "Да" or len(docs) == page_size
            if not has_more or not docs:
                break
            page += 1
        return all_docs

    def get_documents_period(self, doc_type, start_date, end_date, page_size=50):
        """Для DocOpening и других документов, где нужен Период вместо ДатаС/ДатаПо"""
        if isinstance(start_date, datetime):
            start_date = start_date.strftime("%d.%m.%Y")
        if isinstance(end_date, datetime):
            end_date = end_date.strftime("%d.%m.%Y")

        all_docs = []
        page = 1
        while True:
            result = self._rpc_call("СБИС.СписокДокументов", {
                "Фильтр": {
                    "Тип": doc_type,
                    "Период": {"Начало": start_date, "Конец": end_date},
                    "Навигация": {"РазмерСтраницы": str(page_size), "Страница": str(page)}
                }
            })
            if not result:
                break
            docs = result.get("Документ", []) if isinstance(result, dict) else []
            all_docs.extend(docs)
            nav = result.get("Навигация", {}) if isinstance(result, dict) else {}
            has_more = nav.get("ЕстьЕще", "Нет") == "Да" or len(docs) == page_size
            if not has_more or not docs:
                break
            page += 1
        return all_docs

    def get_document(self, doc_id, doc_type=None):
        params = {"Документ": {"Идентификатор": doc_id}}
        if doc_type:
            params["Документ"]["Тип"] = doc_type
        return self._rpc_call("СБИС.ПрочитатьДокумент", params)

    def get_document_details(self, doc_id):
        return self.get_document(doc_id)

    def _safe_float(self, val):
        if val is None:
            return 0.0
        try:
            return float(str(val).replace(",", ".").replace(" ", ""))
        except:
            return 0.0

    def _download_file(self, url):
        try:
            headers = {"X-SBISAccessToken": self.token}
            resp = requests.get(url, headers=headers, timeout=60, allow_redirects=True)
            resp.raise_for_status()
            return resp.content
        except Exception as e:
            print(f"Download error: {e}")
            return None

    def get_items_from_upd(self, doc_meta):
        items = []
        attachments = doc_meta.get("Вложение", [])
        for att in attachments:
            if att.get("Тип") in ["УпдСчфДоп", "УпдДоп", "СчетФактура", "Торг12"]:
                file_info = att.get("Файл", {})
                file_url = file_info.get("Ссылка", "")
                if not file_url:
                    continue
                xml_data = self._download_file(file_url)
                if not xml_data:
                    continue
                items.extend(self._parse_upd_items(xml_data))
        return items

    def _parse_upd_items(self, xml_data):
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
            print(f"XML parse error: {e}")
        return items

    def get_sr2d_items(self, doc_id):
        result = self._rpc_call("ДокОтгрВх.SR2D", {"Идентификатор": doc_id})
        if result:
            return result.get("Товары") or result.get("Наименования") or []
        return []

    def _retail_get(self, endpoint, params=None):
        if not self._ensure_auth():
            return None
        url = f"{self.retail_url}{endpoint}"
        headers = {"X-SBISAccessToken": self.token}
        try:
            resp = requests.get(url, headers=headers, params=params or {}, timeout=30)
            if resp.status_code == 200:
                return resp.json()
            elif resp.status_code in (401, 403):
                if self.authenticate():
                    headers = {"X-SBISAccessToken": self.token}
                    resp = requests.get(url, headers=headers, params=params or {}, timeout=30)
                    if resp.status_code == 200:
                        return resp.json()
            print(f"Retail GET {endpoint} error: {resp.status_code}")
            return None
        except Exception as e:
            print(f"Retail GET {endpoint} exception: {e}")
            return None

    def get_points(self):
        return self._retail_get("/retail/point/list")

    def get_sales(self, point_id=None, date_from=None, date_to=None, page=0, page_size=50):
        params = {'page': page, 'pageSize': page_size}
        if point_id:
            params['pointId'] = point_id
        if date_from:
            if isinstance(date_from, datetime):
                params['fromDateTime'] = date_from.strftime('%Y-%m-%d %H:%M:%S')
            else:
                params['fromDateTime'] = date_from
        if date_to:
            if isinstance(date_to, datetime):
                params['toDateTime'] = date_to.strftime('%Y-%m-%d %H:%M:%S')
            else:
                params['toDateTime'] = date_to
        return self._retail_get("/retail/order/list", params)

    def get_balances(self, nomenclatures=None, warehouses=None, companies=None, price_list_ids=None):
        params = {}
        if nomenclatures:
            params['nomenclatures'] = ','.join(map(str, nomenclatures))
        if warehouses:
            params['warehouses'] = ','.join(map(str, warehouses))
        if companies:
            params['companies'] = ','.join(map(str, companies))
        if price_list_ids:
            params['priceListIds'] = ','.join(map(str, price_list_ids))
        return self._retail_get("/retail/nomenclature/balances", params)

    def get_nomenclature_list(self, point_id, price_list_id=None, with_balance=True, page=0, page_size=100):
        params = {
            'pointId': point_id,
            'withBalance': 'true' if with_balance else 'false',
            'page': page,
            'pageSize': page_size
        }
        if price_list_id:
            params['priceListId'] = price_list_id
        return self._retail_get("/retail/nomenclature/list", params)

    def get_sales_by_period(self, point_id=None, days=7):
        date_to = datetime.now()
        date_from = date_to - timedelta(days=days)
        all_orders = []
        page = 0
        while True:
            result = self.get_sales(point_id=point_id, date_from=date_from, date_to=date_to, page=page, page_size=100)
            if not result:
                break
            orders = result.get('orders', []) if isinstance(result, dict) else result
            if not orders:
                break
            all_orders.extend(orders)
            outcome = result.get('outcome', {}) if isinstance(result, dict) else {}
            has_more = outcome.get('hasMore', False) if isinstance(outcome, dict) else False
            if not has_more:
                break
            page += 1
            import time
            time.sleep(0.2)
        return all_orders

    def get_sales_by_period_monthly(self, point_id=None, days=365):
        import time
        date_to = datetime.now()
        date_from = date_to - timedelta(days=days)
        all_orders = []
        current_month = date_from
        while current_month < date_to:
            month_end = min(
                (current_month.replace(day=1) + timedelta(days=32)).replace(day=1) - timedelta(days=1),
                date_to
            )
            print(f"Loading: {current_month.strftime('%Y-%m-%d')} -> {month_end.strftime('%Y-%m-%d')}")
            page = 0
            month_orders = 0
            while True:
                result = self.get_sales(point_id=point_id, date_from=current_month, date_to=month_end, page=page, page_size=100)
                if not result:
                    break
                orders = result.get('orders', []) if isinstance(result, dict) else result
                if not orders:
                    break
                all_orders.extend(orders)
                month_orders += len(orders)
                outcome = result.get('outcome', {}) if isinstance(result, dict) else {}
                has_more = outcome.get('hasMore', False) if isinstance(outcome, dict) else False
                if not has_more:
                    break
                page += 1
                time.sleep(0.2)
            print(f"  Month loaded: {month_orders} orders")
            current_month = month_end + timedelta(days=1)
        print(f"Total loaded: {len(all_orders)} orders")
        return all_orders

    def get_all_nomenclature(self, point_id, price_list_id=None, with_balance=True):
        import time
        page = 0
        all_items = []
        while True:
            result = self.get_nomenclature_list(point_id=point_id, price_list_id=price_list_id, with_balance=with_balance, page=page, page_size=100)
            if not result:
                break
            items = result.get('nomenclatures', result.get('items', []))
            if not items:
                break
            all_items.extend(items)
            if len(items) < 100:
                break
            page += 1
            time.sleep(0.1)
        return all_items

    def get_doc_openings(self, start_date, end_date):
        """Вскрытия кег (DocOpening) — через Период"""
        return self.get_documents_period('DocOpening', start_date, end_date)

    def get_writeoffs(self, start_date, end_date):
        """Акты списания — через ДатаС/ДатаПо"""
        return self.get_documents('АктСписания', start_date, end_date)

    def get_sales_docs(self, start_date, end_date):
        """Розничные продажи (ДокОтгрИсх) — через ДатаС/ДатаПо"""
        return self.get_documents('ДокОтгрИсх', start_date, end_date)

    def get_doc_items_from_attachment(self, doc_id, doc_type):
        """Номенклатура из ВложениеУчета (XML)"""
        doc = self.get_document(doc_id, doc_type)
        if not doc or 'ВложениеУчета' not in doc:
            return []
        attachments = doc['ВложениеУчета']
        if not attachments or 'Файл' not in attachments[0]:
            return []
        file_url = attachments[0]['Файл'].get('Ссылка')
        if not file_url:
            return []
        try:
            resp = requests.get(file_url, headers=self.headers, timeout=30)
            if resp.status_code != 200:
                return []
            xml_text = resp.text
            if doc_type == 'ДокОтгрИсх':
                return self._parse_upd_xml(xml_text)
            else:
                return self._parse_act_xml(xml_text)
        except Exception as e:
            print(f"Attachment error: {e}")
            return []

    def get_doc_relations(self, doc_id, doc_type):
        """Связи документа (основания и следствия)"""
        doc = self.get_document(doc_id, doc_type)
        if not doc:
            return {'base': [], 'consequence': []}
        result = {'base': [], 'consequence': []}
        if 'ДокументОснование' in doc:
            for item in doc['ДокументОснование']:
                d = item.get('Документ', {})
                result['base'].append({
                    'type': d.get('Тип'), 'number': d.get('Номер'),
                    'date': d.get('Дата'), 'id': d.get('Идентификатор')
                })
        if 'ДокументСледствие' in doc:
            for item in doc['ДокументСледствие']:
                d = item.get('Документ', {})
                result['consequence'].append({
                    'type': d.get('Тип'), 'number': d.get('Номер'),
                    'date': d.get('Дата'), 'id': d.get('Идентификатор')
                })
        return result

    def _parse_act_xml(self, xml_text):
        """Парсинг XML Акта/DocOpening (ТаблТовар)"""
        items = []
        try:
            root = ET.fromstring(xml_text)
            for doc in root.iter('Документ'):
                for tabl in doc.iter('ТаблТовар'):
                    for row in tabl.iter('СтрТабл'):
                        item = {
                            'name': row.get('Наименование', ''),
                            'quantity': self._safe_float(row.get('Количество', 0)),
                            'unit': row.get('ЕдИзм', ''),
                            'price': self._safe_float(row.get('Цена', 0)),
                            'sum': self._safe_float(row.get('Сумма', 0)),
                            'sku': row.get('НомНомер', ''),
                            'gtin': row.get('ГТИН', ''),
                            'alc_code': ''
                        }
                        for param in row.iter('Параметр'):
                            if param.get('Имя') == 'AlcCode':
                                item['alc_code'] = param.get('Значение', '')
                        items.append(item)
        except Exception as e:
            print(f"Act XML parse error: {e}")
        return items

    def _parse_upd_xml(self, xml_text):
        """Парсинг УПД (ДокОтгрИсх) — ТаблСчФакт"""
        items = []
        try:
            root = ET.fromstring(xml_text)
            for doc in root.iter('Документ'):
                for tabl in doc.iter('ТаблСчФакт'):
                    for row in tabl.iter('СведТов'):
                        items.append({
                            'name': row.get('НаимТов', ''),
                            'quantity': self._safe_float(row.get('КолТов', 0)),
                            'unit': row.get('НаимЕдИзм', ''),
                            'price': self._safe_float(row.get('ЦенаТов', 0)),
                            'sum': self._safe_float(row.get('СтТовБезНДС', 0)),
                            'sku': '', 'gtin': '', 'alc_code': ''
                        })
        except Exception as e:
            print(f"UPD XML parse error: {e}")
        return items


def create_sbis_api_from_config(config):
    return SbisAPI(
        token=config.get('SBIS_TOKEN', ''),
        client_id=config.get('SBIS_CLIENT_ID', ''),
        app_secret=config.get('SBIS_APP_SECRET', ''),
        secret_key=config.get('SBIS_SECRET_KEY', '')
    )


def get_last_sync_date(db_model):
    return datetime.utcnow() - timedelta(days=365)

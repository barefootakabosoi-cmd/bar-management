import os


os.makedirs('templates', exist_ok=True)

# === sbis_api.py ===
sbis_api = r'''import requests
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
        self.headers = {"Content-Type": "application/json-rpc;charset=utf-8", "Accept": "application/json"}

    def authenticate(self):
        url = f"{self.base_url}/oauth/service/"
        payload = {"app_client_id": self.client_id, "app_secret": self.app_secret, "secret_key": self.secret_key}
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
            print(f"Auth failed: {resp.status_code}")
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
                "Фильтр": {"Тип": doc_type, "ДатаС": date_from, "ДатаПо": date_to,
                           "Навигация": {"РазмерСтраницы": str(page_size), "Страница": str(page)}})
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
        params = {'pointId': point_id, 'withBalance': 'true' if with_balance else 'false', 'page': page, 'pageSize': page_size}
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
            month_end = min((current_month.replace(day=1) + timedelta(days=32)).replace(day=1) - timedelta(days=1), date_to)
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

    # V8
    def get_doc_openings(self, start_date, end_date):
        return self.get_documents('DocOpening', start_date, end_date)

    def get_writeoffs(self, start_date, end_date):
        return self.get_documents('АктСписания', start_date, end_date)

    def get_sales_docs(self, start_date, end_date):
        return self.get_documents('ДокОтгрИсх', start_date, end_date)

    def get_doc_items_from_attachment(self, doc_id, doc_type):
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
        doc = self.get_document(doc_id, doc_type)
        if not doc:
            return {'base': [], 'consequence': []}
        result = {'base': [], 'consequence': []}
        if 'ДокументОснование' in doc:
            for item in doc['ДокументОснование']:
                d = item.get('Документ', {})
                result['base'].append({'type': d.get('Тип'), 'number': d.get('Номер'), 'date': d.get('Дата'), 'id': d.get('Идентификатор')})
        if 'ДокументСледствие' in doc:
            for item in doc['ДокументСледствие']:
                d = item.get('Документ', {})
                result['consequence'].append({'type': d.get('Тип'), 'number': d.get('Номер'), 'date': d.get('Дата'), 'id': d.get('Идентификатор')})
        return result

    def _parse_act_xml(self, xml_text):
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
'''

with open('sbis_api.py', 'w', encoding='utf-8') as f:
    f.write(sbis_api)
print('sbis_api.py OK')

# === sync_retail.py ===
sync_retail = r'''#!/usr/bin/env python3
import os
import sys
import argparse
import logging
import json
import time
from datetime import datetime, timedelta

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[logging.StreamHandler(), logging.FileHandler('sync_retail.log', encoding='utf-8')]
)
logger = logging.getLogger(__name__)

try:
    from config import Config
    from models import db, StockBalance, SaleRecord, DailySalesSummary
    from app import app as flask_app
except ImportError as e:
    logger.error("Не удалось импортировать модули проекта: %s", e)
    sys.exit(1)

app_context = flask_app.app_context()
app_context.push()

from sbis_api import SbisAPI


class RetailSync:
    def __init__(self):
        self.sbis = SbisAPI(
            token=Config.SBIS_TOKEN,
            client_id=Config.SBIS_CLIENT_ID,
            app_secret=Config.SBIS_APP_SECRET,
            secret_key=Config.SBIS_SECRET_KEY
        )
        self.point_id = self._parse_id(Config.SBIS_POINT_ID, 'point')
        self.warehouse_id = self._parse_id(Config.SBIS_WAREHOUSE_ID, 'warehouse', required=False)
        self.company_id = self._parse_id(Config.SBIS_COMPANY_ID, 'company', required=False)
        self.price_list_id = self._parse_id(Config.SBIS_PRICE_LIST_ID, 'price_list', required=False)

    def _parse_id(self, value, name, required=True):
        try:
            parsed = int(value) if value and str(value).strip() and str(value).strip().lower() not in ('', 'your-' + name + '-id', 'none', 'null') else None
        except (ValueError, AttributeError):
            parsed = None
        if required and not parsed:
            logger.error(f"SBIS_{name.upper()}_ID не настроен! Добавьте в .env")
            sys.exit(1)
        return parsed

    def sync_sales(self, days=365):
        logger.info("=" * 60)
        logger.info("СИНХРОНИЗАЦИЯ ПРОДАЖ за %d дней", days)
        logger.info("Точка: %s", self.point_id)
        logger.info("=" * 60)

        date_to = datetime.now()
        date_from = date_to - timedelta(days=days)
        total_imported = 0
        total_updated = 0
        current = date_from

        while current < date_to:
            month_end = min((current.replace(day=1) + timedelta(days=32)).replace(day=1) - timedelta(days=1), date_to)
            logger.info("Месяц: %s → %s", current.strftime('%Y-%m-%d'), month_end.strftime('%Y-%m-%d'))

            month_imported = 0
            month_updated = 0
            page = 0

            while True:
                result = self.sbis.get_sales(point_id=self.point_id, date_from=current, date_to=month_end, page=page, page_size=100)
                if not result:
                    break

                raw_orders = result.get('orders', {}) if isinstance(result, dict) else {}
                if isinstance(raw_orders, dict):
                    orders = list(raw_orders.values())
                else:
                    orders = raw_orders if isinstance(raw_orders, list) else []

                if not orders:
                    break

                for order_data in orders:
                    is_new = self._save_sale(order_data)
                    if is_new:
                        month_imported += 1
                    else:
                        month_updated += 1

                outcome = result.get('outcome', {}) if isinstance(result, dict) else {}
                has_more = outcome.get('hasMore', False) if isinstance(outcome, dict) else False
                logger.info(" Страница %d: %d заказов, hasMore=%s", page, len(orders), has_more)

                if not has_more:
                    break
                page += 1
                time.sleep(0.2)

            logger.info(" Месяц: %d новых, %d обновлено", month_imported, month_updated)
            total_imported += month_imported
            total_updated += month_updated
            current = month_end + timedelta(days=1)

        logger.info("=" * 60)
        logger.info("ИТОГО: %d новых, %d обновлено", total_imported, total_updated)
        logger.info("=" * 60)

        self._recalculate_daily_sales()
        return total_imported

    def _save_sale(self, order_data):
        order_id = str(order_data.get('Key', order_data.get('id', '')))
        if not order_id:
            return False

        sale = SaleRecord.query.filter_by(sbis_order_id=order_id).first()
        is_new = sale is None

        if not sale:
            sale = SaleRecord(sbis_order_id=order_id)
            db.session.add(sale)

        sale.order_number = str(order_data.get('Number', ''))

        date_str = order_data.get('DateWTZ', order_data.get('OpenedWTZ', order_data.get('date', '')))
        if date_str:
            try:
                date_str = str(date_str).replace('Z', '+00:00')
                if '.' in date_str:
                    sale.date = datetime.strptime(date_str.split('.')[0], '%Y-%m-%d %H:%M:%S')
                else:
                    sale.date = datetime.fromisoformat(date_str)
            except Exception as e:
                logger.warning("Не удалось распарсить дату %s: %s", date_str, e)
                sale.date = None
        else:
            sale.date = None

        sale.point_id = str(order_data.get('Company', self.point_id))
        sale.total_sum = float(order_data.get('Sum', 0) or 0)
        sale.total_sum_with_vat = float(order_data.get('SumWithVat', sale.total_sum) or 0)
        sale.status = 'deleted' if order_data.get('Deleted') else 'active'
        sale.items_json = order_data
        sale.synced_at = datetime.now()

        db.session.commit()
        return is_new

    def _recalculate_daily_sales(self):
        logger.info("Пересчёт дневных агрегатов...")
        DailySalesSummary.query.delete()

        sales = SaleRecord.query.filter(SaleRecord.date != None).all()
        daily = {}
        for sale in sales:
            try:
                if isinstance(sale.date, str):
                    d = datetime.fromisoformat(sale.date.replace('Z', '+00:00')).date()
                elif isinstance(sale.date, datetime):
                    d = sale.date.date()
                else:
                    continue
                if d not in daily:
                    daily[d] = {'orders': 0, 'total': 0, 'total_vat': 0}
                daily[d]['orders'] += 1
                daily[d]['total'] += float(sale.total_sum or 0)
                daily[d]['total_vat'] += float(sale.total_sum_with_vat or 0)
            except Exception as e:
                logger.warning("Ошибка обработки даты для заказа %s: %s", sale.sbis_order_id, e)
                continue

        for d, data in daily.items():
            summary = DailySalesSummary(date=d, total_orders=data['orders'], total_sum=data['total'], total_sum_with_vat=data['total_vat'])
            db.session.add(summary)

        db.session.commit()
        logger.info("Агрегаты обновлены: %d дней", len(daily))

    def sync_balances(self):
        logger.info("=" * 60)
        logger.info("СИНХРОНИЗАЦИЯ ОСТАТКОВ (через номенклатуру)")
        logger.info("=" * 60)

        all_items = []
        page = 0

        while True:
            result = self.sbis.get_nomenclature_list(point_id=self.point_id, price_list_id=self.price_list_id, with_balance=True, page=page, page_size=100)
            if not result:
                break

            items = result.get('nomenclatures', result.get('items', []))
            if not items:
                break

            all_items.extend(items)
            logger.info(" Страница %d: %d товаров", page, len(items))

            outcome = result.get('outcome', {}) if isinstance(result, dict) else {}
            has_more = outcome.get('hasMore', False) if isinstance(outcome, dict) else False

            if not has_more:
                break
            page += 1
            time.sleep(0.2)

        logger.info("Всего получено %d товаров", len(all_items))

        StockBalance.query.delete()
        count_with_balance = 0

        for item in all_items:
            balance_val = item.get('balance')
            if balance_val is None:
                continue
            if float(balance_val) <= 0:
                continue

            count_with_balance += 1
            name = item.get('name', item.get('Номенклатура', ''))
            balance = StockBalance(
                sbis_nomenclature_id=str(item.get('id', '')),
                sbis_warehouse_id=str(self.warehouse_id or ''),
                name=name,
                normalized_name=name.lower() if name else '',
                quantity=float(balance_val),
                unit=item.get('unit', item.get('Единица', 'шт')),
            )
            db.session.add(balance)

        db.session.commit()
        logger.info("Сохранено %d позиций с положительными остатками", count_with_balance)
        return count_with_balance

    def sync_nomenclature(self):
        logger.info("=" * 60)
        logger.info("СИНХРОНИЗАЦИЯ НОМЕНКЛАТУРЫ")
        logger.info("=" * 60)

        all_items = []
        page = 0

        while True:
            result = self.sbis.get_nomenclature_list(point_id=self.point_id, price_list_id=self.price_list_id, with_balance=True, page=page, page_size=100)
            if not result:
                break

            items = result.get('nomenclatures', result.get('items', []))
            if not items:
                break

            all_items.extend(items)
            logger.info(" Страница %d: %d товаров", page, len(items))

            outcome = result.get('outcome', {}) if isinstance(result, dict) else {}
            has_more = outcome.get('hasMore', False) if isinstance(outcome, dict) else False
            if not has_more:
                break

            page += 1
            time.sleep(0.2)

        logger.info("Всего получено %d товаров", len(all_items))

        with open('nomenclature_cache.json', 'w', encoding='utf-8') as f:
            json.dump(all_items, f, ensure_ascii=False, indent=2)

        logger.info("Сохранено в nomenclature_cache.json")
        return len(all_items)

    def get_stats(self):
        return {
            'sales_total': SaleRecord.query.count(),
            'sales_today': SaleRecord.query.filter(SaleRecord.date >= datetime.now().replace(hour=0, minute=0, second=0)).count(),
            'sales_month': SaleRecord.query.filter(SaleRecord.date >= datetime.now().replace(day=1, hour=0, minute=0, second=0)).count(),
            'balances_total': StockBalance.query.count(),
            'daily_summaries': DailySalesSummary.query.count()
        }


def test_points():
    sync = RetailSync()
    points = sync.sbis.get_points()
    print("\nТорговые точки:")
    if isinstance(points, dict) and 'salesPoints' in points:
        for p in points['salesPoints']:
            print(f" ID: {p.get('id')}, Название: {p.get('name')}")
    elif isinstance(points, list):
        for p in points:
            print(f" ID: {p.get('id')}, Название: {p.get('name')}")
    else:
        print(f" Ответ: {points}")


def main():
    parser = argparse.ArgumentParser(description='Синхронизация СБИС Retail API v8')
    parser.add_argument('--sales', action='store_true', help='Синхронизировать продажи')
    parser.add_argument('--balances', action='store_true', help='Синхронизировать остатки')
    parser.add_argument('--nomenclature', action='store_true', help='Синхронизировать номенклатуру')
    parser.add_argument('--all', action='store_true', help='Синхронизировать всё')
    parser.add_argument('--days', type=int, default=365, help='Период в днях')
    parser.add_argument('--stats', action='store_true', help='Показать статистику')
    parser.add_argument('--test-points', action='store_true', help='Показать торговые точки')

    args = parser.parse_args()

    if args.test_points:
        test_points()
        return

    if args.stats:
        sync = RetailSync()
        stats = sync.get_stats()
        print("\n" + "=" * 40)
        print("СТАТИСТИКА")
        print("=" * 40)
        for key, value in stats.items():
            print(f" {key}: {value}")
        return

    if not any([args.sales, args.balances, args.nomenclature, args.all]):
        parser.print_help()
        return

    sync = RetailSync()

    try:
        if args.sales or args.all:
            sync.sync_sales(args.days)
        if args.balances or args.all:
            sync.sync_balances()
        if args.nomenclature or args.all:
            sync.sync_nomenclature()

        stats = sync.get_stats()
        print("\n" + "=" * 40)
        print("СИНХРОНИЗАЦИЯ ЗАВЕРШЕНА")
        print("=" * 40)
        for key, value in stats.items():
            print(f" {key}: {value}")

    except Exception as e:
        logger.exception("Критическая ошибка")
        print(f"\n❌ Ошибка: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
'''

with open('sync_retail.py', 'w', encoding='utf-8') as f:
    f.write(sync_retail)
print('sync_retail.py OK')

# === patch_models_v8.py ===
models_patch = r'''
# ========== V8: DocOpening / АктСписания / KegRetailMapping ==========

class KegOpening(db.Model):
    __tablename__ = 'keg_openings'
    id = db.Column(db.Integer, primary_key=True)
    doc_number = db.Column(db.String(50))
    doc_date = db.Column(db.Date)
    name = db.Column(db.String(500))
    quantity = db.Column(db.Float)
    unit = db.Column(db.String(20))
    price = db.Column(db.Float)
    sum = db.Column(db.Float)
    sku = db.Column(db.String(100))
    alc_code = db.Column(db.String(50))
    gtin = db.Column(db.String(50))
    is_mapped = db.Column(db.Boolean, default=False)
    mapped_retail_name = db.Column(db.String(500))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class Writeoff(db.Model):
    __tablename__ = 'writeoffs'
    id = db.Column(db.Integer, primary_key=True)
    doc_number = db.Column(db.String(50))
    doc_date = db.Column(db.Date)
    writeoff_type = db.Column(db.String(50))
    note = db.Column(db.Text)
    name = db.Column(db.String(500))
    quantity = db.Column(db.Float)
    unit = db.Column(db.String(20))
    price = db.Column(db.Float)
    sum = db.Column(db.Float)
    sku = db.Column(db.String(100))
    alc_code = db.Column(db.String(50))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class KegRetailMapping(db.Model):
    __tablename__ = 'keg_retail_mapping'
    id = db.Column(db.Integer, primary_key=True)
    keg_name = db.Column(db.String(500), unique=True)
    retail_name = db.Column(db.String(500))
    alc_code = db.Column(db.String(50))
    liters_per_keg = db.Column(db.Float, default=30.0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
'''

with open('patch_models_v8.py', 'w', encoding='utf-8') as f:
    f.write(models_patch)
print('patch_models_v8.py OK')

# === templates ===
templates = {
    'v8_openings.html': r'''{% extends "base.html" %}
{% block title %}Вскрытия кег{% endblock %}
{% block content %}
<div class="container mt-4">
  <h2>Вскрытия кег (DocOpening)</h2>
  <form method="get" class="row g-3 mb-3">
    <div class="col-auto"><input type="date" name="start" class="form-control" value="{{ start }}"></div>
    <div class="col-auto"><input type="date" name="end" class="form-control" value="{{ end }}"></div>
    <div class="col-auto"><button type="submit" class="btn btn-primary">Фильтр</button></div>
  </form>
  <form method="post" action="{{ url_for('v8_sync_docs') }}" class="mb-3">
    <input type="hidden" name="days" value="30">
    <button type="submit" class="btn btn-success">Синхронизировать</button>
  </form>
  <table class="table table-striped">
    <thead><tr><th>Дата</th><th>№</th><th>Номенклатура</th><th>Кол-во</th><th>Ед.</th><th>Цена</th><th>Сумма</th><th>AlcCode</th><th>Связь</th></tr></thead>
    <tbody>
    {% for item in items %}
      <tr>
        <td>{{ item.doc_date.strftime('%d.%m.%Y') if item.doc_date else '-' }}</td>
        <td>{{ item.doc_number or '-' }}</td>
        <td>{{ item.name or '-' }}</td>
        <td>{{ item.quantity or 0 }}</td>
        <td>{{ item.unit or '-' }}</td>
        <td>{{ "%.2f"|format(item.price or 0) }} ₽</td>
        <td>{{ "%.2f"|format(item.sum or 0) }} ₽</td>
        <td><code>{{ item.alc_code or '-' }}</code></td>
        <td>{% if item.is_mapped %}<span class="badge bg-success">{{ item.mapped_retail_name }}</span>{% else %}<span class="badge bg-secondary">Не связана</span>{% endif %}</td>
      </tr>
    {% else %}
      <tr><td colspan="9" class="text-center text-muted">Нет данных</td></tr>
    {% endfor %}
    </tbody>
  </table>
</div>
{% endblock %}''',

    'v8_writeoffs.html': r'''{% extends "base.html" %}
{% block title %}Списания{% endblock %}
{% block content %}
<div class="container mt-4">
  <h2>Списания (АктСписания)</h2>
  <form method="get" class="row g-3 mb-3">
    <div class="col-auto"><input type="date" name="start" class="form-control" value="{{ start }}"></div>
    <div class="col-auto"><input type="date" name="end" class="form-control" value="{{ end }}"></div>
    <div class="col-auto"><button type="submit" class="btn btn-primary">Фильтр</button></div>
  </form>
  <table class="table table-striped">
    <thead><tr><th>Дата</th><th>№</th><th>Тип</th><th>Примечание</th><th>Номенклатура</th><th>Кол-во</th><th>Сумма</th></tr></thead>
    <tbody>
    {% for item in items %}
      <tr>
        <td>{{ item.doc_date.strftime('%d.%m.%Y') if item.doc_date else '-' }}</td>
        <td>{{ item.doc_number or '-' }}</td>
        <td><span class="badge bg-{{ 'danger' if item.writeoff_type == 'брак' else 'warning' if item.writeoff_type == 'отключение_крана' else 'secondary' }}">{{ item.writeoff_type }}</span></td>
        <td>{{ item.note or '-' }}</td>
        <td>{{ item.name or '-' }}</td>
        <td>{{ item.quantity or 0 }} {{ item.unit or '' }}</td>
        <td>{{ "%.2f"|format(item.sum or 0) }} ₽</td>
      </tr>
    {% else %}
      <tr><td colspan="7" class="text-center text-muted">Нет данных</td></tr>
    {% endfor %}
    </tbody>
  </table>
</div>
{% endblock %}''',

    'v8_sales_docs.html': r'''{% extends "base.html" %}
{% block title %}Розничные продажи{% endblock %}
{% block content %}
<div class="container mt-4">
  <h2>Розничные продажи (ДокОтгрИсх)</h2>
  <form method="get" class="row g-3 mb-3">
    <div class="col-auto"><input type="date" name="start" class="form-control" value="{{ start }}"></div>
    <div class="col-auto"><input type="date" name="end" class="form-control" value="{{ end }}"></div>
    <div class="col-auto"><button type="submit" class="btn btn-primary">Фильтр</button></div>
  </form>
  <table class="table table-striped">
    <thead><tr><th>Дата</th><th>Документ</th><th>Товар</th><th>Кол-во</th><th>Цена</th><th>Сумма</th></tr></thead>
    <tbody>
    {% for item in items %}
      <tr>
        <td>{{ item.document.doc_date.strftime('%d.%m.%Y') if item.document and item.document.doc_date else '-' }}</td>
        <td>{{ item.document.doc_number or '-' }}</td>
        <td>{{ item.product_name or '-' }}</td>
        <td>{{ item.quantity or 0 }} {{ item.unit or '' }}</td>
        <td>{{ "%.2f"|format(item.price or 0) }} ₽</td>
        <td>{{ "%.2f"|format(item.total or 0) }} ₽</td>
      </tr>
    {% else %}
      <tr><td colspan="6" class="text-center text-muted">Нет данных</td></tr>
    {% endfor %}
    </tbody>
  </table>
</div>
{% endblock %}'''
}

for name, content in templates.items():
    with open(f'templates/{name}', 'w', encoding='utf-8') as f:
        f.write(content)
    print(f'templates/{name} OK')

print('\n' + '='*50)
print('ВСЕ ФАЙЛЫ СОЗДАНЫ!')
print('Осталось:')
print('1. Добавить patch_models_v8.py в конец models.py')
print('2. Добавить v8 роуты в конец app.py (перед if __name__)')
print('3. rm bar_management.db && flask init-db')
print('4. python app.py')
print('='*50)

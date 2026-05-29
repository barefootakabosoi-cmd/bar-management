#!/usr/bin/env python3
"""
Монолитный скрипт синхронизации Retail API СБИС
Всё в одном файле — не зависит от sbis_api.py
"""

import os
import sys
import argparse
import logging
import json
import requests
import time
from datetime import datetime, timedelta
import time
# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('sync_retail.log', encoding='utf-8')
    ]
)
logger = logging.getLogger(__name__)

# Импорты Flask
try:
    from config import Config
    from models import db, StockBalance, SaleRecord, DailySalesSummary
    from app import app as flask_app
except ImportError as e:
    logger.error("Не удалось импортировать модули проекта: %s", e)
    sys.exit(1)

app_context = flask_app.app_context()
app_context.push()


# ==================== SBIS RETAIL API ====================

class SbisRetailAPI:
    """Клиент для Retail API СБИС (api.sbis.ru)"""

    def __init__(self, token=None, client_id=None, app_secret=None, secret_key=None):
        self.token = token
        self.client_id = client_id
        self.app_secret = app_secret
        self.secret_key = secret_key
        self.retail_url = "https://api.sbis.ru"
        self.base_url = "https://online.sbis.ru"

    def authenticate(self):
        """OAuth аутентификация"""
        url = f"{self.base_url}/oauth/service/"
        payload = {
            "client_id": self.client_id,
            "client_secret": self.app_secret,
            "secret_key": self.secret_key,
            "grant_type": "client_credentials"
        }
        try:
            resp = requests.post(url, json=payload, timeout=30)
            print(f"OAuth response: {resp.status_code}")
            if resp.status_code == 200:
                data = resp.json()
                self.token = data.get("access_token")
                print("Authenticated successfully")
                return True
            else:
                print(f"Auth error: {resp.status_code}, {resp.text[:200]}")
                return False
        except Exception as e:
            print(f"Auth exception: {e}")
            return False

    def get_points(self):
        """GET /retail/point/list"""
        if not self.token:
            if not self.authenticate():
                return []

        url = f"{self.retail_url}/retail/point/list"
        headers = {"X-SBISAccessToken": self.token}

        try:
            resp = requests.get(url, headers=headers, timeout=30)
            print(f"Points: {resp.status_code}")
            if resp.status_code == 200:
                return resp.json()
            elif resp.status_code == 401:
                if self.authenticate():
                    headers = {"X-SBISAccessToken": self.token}
                    resp = requests.get(url, headers=headers, timeout=30)
                    if resp.status_code == 200:
                        return resp.json()
                return []
            else:
                print(f"Points error: {resp.status_code}, {resp.text[:200]}")
                return []
        except Exception as e:
            print(f"Points exception: {e}")
            return []

    def get_sales(self, point_id=None, date_from=None, date_to=None, page=0, page_size=50):
        """GET /retail/order/list"""
        if not self.token:
            if not self.authenticate():
                return []

        url = f"{self.retail_url}/retail/order/list"
        headers = {"X-SBISAccessToken": self.token}

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

        try:
            resp = requests.get(url, headers=headers, params=params, timeout=30)
            print(f"Sales: {resp.status_code}, params={params}")
            if resp.status_code == 200:
                return resp.json()
            elif resp.status_code == 401:
                if self.authenticate():
                    headers = {"X-SBISAccessToken": self.token}
                    resp = requests.get(url, headers=headers, params=params, timeout=30)
                    if resp.status_code == 200:
                        return resp.json()
                return []
            else:
                print(f"Sales error: {resp.status_code}, {resp.text[:200]}")
                return []
        except Exception as e:
            print(f"Sales exception: {e}")
            return []

    def get_balances(self, nomenclatures=None, warehouses=None, companies=None, price_list_ids=None):
        """GET /retail/nomenclature/balances"""
        if not self.token:
            if not self.authenticate():
                return []

        url = f"{self.retail_url}/retail/nomenclature/balances"
        headers = {"X-SBISAccessToken": self.token}

        params = {}
        if nomenclatures:
            params['nomenclatures'] = ','.join(map(str, nomenclatures))
        if warehouses:
            params['warehouses'] = ','.join(map(str, warehouses))
        if companies:
            params['companies'] = ','.join(map(str, companies))
        if price_list_ids:
            params['priceListIds'] = ','.join(map(str, price_list_ids))

        try:
            resp = requests.get(url, headers=headers, params=params, timeout=30)
            print(f"Balances: {resp.status_code}")
            if resp.status_code == 200:
                return resp.json()
            elif resp.status_code == 401:
                if self.authenticate():
                    headers = {"X-SBISAccessToken": self.token}
                    resp = requests.get(url, headers=headers, params=params, timeout=30)
                    if resp.status_code == 200:
                        return resp.json()
                return []
            else:
                print(f"Balances error: {resp.status_code}, {resp.text[:200]}")
                return []
        except Exception as e:
            print(f"Balances exception: {e}")
            return []

    def get_nomenclature_list(self, point_id, price_list_id=None, with_balance=True, page=0, page_size=100):
        """GET /retail/nomenclature/list с пагинацией"""
        if not self.token:
            if not self.authenticate():
                return []

        url = f"{self.retail_url}/retail/nomenclature/list"
        headers = {"X-SBISAccessToken": self.token}

        params = {
            'pointId': point_id,
            'withBalance': 'true' if with_balance else 'false',
            'page': page,
            'pageSize': page_size
        }
        if price_list_id:
            params['priceListId'] = price_list_id

        try:
            resp = requests.get(url, headers=headers, params=params, timeout=30)
            print(f"Nomenclature: {resp.status_code}, page={page}")
            if resp.status_code == 200:
                return resp.json()
            elif resp.status_code == 401:
                if self.authenticate():
                    headers = {"X-SBISAccessToken": self.token}
                    resp = requests.get(url, headers=headers, params=params, timeout=30)
                    if resp.status_code == 200:
                        return resp.json()
                return []
            else:
                print(f"Nomenclature error: {resp.status_code}, {resp.text[:200]}")
                return []
        except Exception as e:
            print(f"Nomenclature exception: {e}")
            return []
class RetailSync:
    def __init__(self):
        self.sbis = SbisRetailAPI(
            token=Config.SBIS_TOKEN,
            client_id=Config.SBIS_CLIENT_ID,
            app_secret=Config.SBIS_APP_SECRET,
            secret_key=Config.SBIS_SECRET_KEY
        )

        # Парсим ID
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
            month_end = min(
                (current.replace(day=1) + timedelta(days=32)).replace(day=1) - timedelta(days=1),
                date_to
            )

            logger.info("Месяц: %s → %s", current.strftime('%Y-%m-%d'), month_end.strftime('%Y-%m-%d'))

            month_imported = 0
            month_updated = 0
            page = 0

            while True:
                result = self.sbis.get_sales(
                    point_id=self.point_id,
                    date_from=current,
                    date_to=month_end,
                    page=page,
                    page_size=100
                )

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

                # Проверяем hasMore
                outcome = result.get('outcome', {}) if isinstance(result, dict) else {}
                has_more = outcome.get('hasMore', False) if isinstance(outcome, dict) else False

                logger.info("  Страница %d: %d заказов, hasMore=%s", page, len(orders), has_more)

                if not has_more:
                    break

                page += 1
                time.sleep(0.2)

            logger.info("  Месяц: %d новых, %d обновлено", month_imported, month_updated)
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
                # Парсим разные форматы даты
                date_str = str(date_str).replace('Z', '+00:00')
                if '.' in date_str:
                    # Формат: 2026-05-29 14:14:47.954810
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
        from sqlalchemy import func
        from datetime import date as dt_date

        logger.info("Пересчёт дневных агрегатов...")
        DailySalesSummary.query.delete()

        # Группируем вручную, чтобы избежать проблем с cast
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
            summary = DailySalesSummary(
                date=d,
                total_orders=data['orders'],
                total_sum=data['total'],
                total_sum_with_vat=data['total_vat']
            )
            db.session.add(summary)

        db.session.commit()
        logger.info("Агрегаты обновлены: %d дней", len(daily))

    def sync_balances(self):
        """Синхронизация остатков через номенклатуру (with_balance=True)"""
    def sync_balances(self):
        """Синхронизация остатков через номенклатуру (только >0)"""
        logger.info("=" * 60)
        logger.info("СИНХРОНИЗАЦИЯ ОСТАТКОВ (через номенклатуру)")
        logger.info("=" * 60)

        all_items = []
        page = 0

        while True:
            result = self.sbis.get_nomenclature_list(
                point_id=self.point_id,
                price_list_id=self.price_list_id,
                with_balance=True,
                page=page,
                page_size=100
            )

            if not result:
                break

            items = result.get('nomenclatures', result.get('items', []))
            if not items:
                break

            all_items.extend(items)
            logger.info("  Страница %d: %d товаров", page, len(items))

            # Проверяем hasMore
            outcome = result.get('outcome', {}) if isinstance(result, dict) else {}
            has_more = outcome.get('hasMore', False) if isinstance(outcome, dict) else False
            logger.info("  hasMore=%s", has_more)

            if not has_more:
                break

            page += 1
            time.sleep(0.2)

        logger.info("Всего получено %d товаров", len(all_items))

        # Сохраняем остатки в БД (только > 0)
        StockBalance.query.delete()

        count_with_balance = 0
        for item in all_items:
            balance_val = item.get('balance')
            if balance_val is None:
                continue
            if float(balance_val) <= 0:
                continue  # Пропускаем нулевые и отрицательные

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
        logger.info("Сохранено %d позиций с остатками", count_with_balance)
        return count_with_balance

    def sync_nomenclature(self):
        logger.info("=" * 60)
        logger.info("СИНХРОНИЗАЦИЯ НОМЕНКЛАТУРЫ")
        logger.info("=" * 60)

        all_items = []
        page = 0

        while True:
            result = self.sbis.get_nomenclature_list(
                point_id=self.point_id,
                price_list_id=self.price_list_id,
                with_balance=True
            )

            if not result:
                break

            items = result.get('nomenclatures', result.get('items', []))
            if not items:
                break

            all_items.extend(items)
            logger.info("  Страница %d: %d товаров", page, len(items))

            if len(items) < 100:
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
            'sales_today': SaleRecord.query.filter(
                SaleRecord.date >= datetime.now().replace(hour=0, minute=0, second=0)
            ).count(),
            'sales_month': SaleRecord.query.filter(
                SaleRecord.date >= datetime.now().replace(day=1, hour=0, minute=0, second=0)
            ).count(),
            'balances_total': StockBalance.query.count(),
            'daily_summaries': DailySalesSummary.query.count()
        }


def test_points():
    sync = RetailSync()
    points = sync.sbis.get_points()
    print("\nТорговые точки:")
    if isinstance(points, dict) and 'salesPoints' in points:
        for p in points['salesPoints']:
            print(f"  ID: {p.get('id')}, Название: {p.get('name')}")
    elif isinstance(points, list):
        for p in points:
            print(f"  ID: {p.get('id')}, Название: {p.get('name')}")
    else:
        print(f"  Ответ: {points}")


def main():
    parser = argparse.ArgumentParser(description='Синхронизация СБИС Retail API')
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
            print(f"  {key}: {value}")
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
            print(f"  {key}: {value}")

    except Exception as e:
        logger.exception("Критическая ошибка")
        print(f"\n❌ Ошибка: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()

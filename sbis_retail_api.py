import requests
from datetime import datetime
from sbis_api import SbisAPI

class SbisRetailAPI(SbisAPI):
    """Расширение SbisAPI для Retail API (api.sbis.ru)"""

    def __init__(self, token=None, client_id=None, app_secret=None, secret_key=None):
        super().__init__(token, client_id, app_secret, secret_key)
        self.retail_url = "https://api.sbis.ru"

    def get_points(self):
        """GET /retail/point/list — список торговых точек"""
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
        """GET /retail/order/list — продажи"""
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
        """GET /retail/nomenclature/balances — остатки"""
        if not self.token:
            if not self.authenticate():
                return []

        url = f"{self.retail_url}/retail/nomenclature/balances"
        headers = {"X-SBISAccessToken": self.token}

        # Используем список кортежей для массивов (companies[], warehouses[], nomenclatures[])
        params = []
        if companies:
            for c in companies:
                params.append(('companies[]', c))
        if warehouses:
            for w in warehouses:
                params.append(('warehouses[]', w))
        if nomenclatures:
            for n in nomenclatures:
                params.append(('nomenclatures[]', n))
        if price_list_ids:
            for p in price_list_ids:
                params.append(('priceListIds[]', p))

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

    def get_nomenclature_list(self, point_id, price_list_id=None, with_balance=True):
        """GET /retail/v2/nomenclature/list — номенклатура с остатками"""
        if not self.token:
            if not self.authenticate():
                return []

        url = f"{self.retail_url}/retail/v2/nomenclature/list"
        headers = {"X-SBISAccessToken": self.token}

        params = {
            'pointId': point_id,
            'withBalance': 'true' if with_balance else 'false',
            'pageSize': 100
        }
        if price_list_id:
            params['priceListId'] = price_list_id

        try:
            resp = requests.get(url, headers=headers, params=params, timeout=30)
            print(f"Nomenclature v2: {resp.status_code}")
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
                print(f"Nomenclature v2 error: {resp.status_code}, {resp.text[:200]}")
                return []
        except Exception as e:
            print(f"Nomenclature v2 exception: {e}")
            return []

    def get_sales_by_period(self, point_id=None, days=7):
        """Продажи за период с пагинацией"""
        from datetime import timedelta
        import time

        date_to = datetime.now()
        date_from = date_to - timedelta(days=days)

        all_orders = []
        page = 0

        while True:
            result = self.get_sales(
                point_id=point_id,
                date_from=date_from,
                date_to=date_to,
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

            all_orders.extend(orders)

            # Проверяем hasMore
            outcome = result.get('outcome', {}) if isinstance(result, dict) else {}
            has_more = outcome.get('hasMore', False) if isinstance(outcome, dict) else False

            print(f"  Страница {page}: {len(orders)} заказов, hasMore={has_more}")

            if not has_more:
                break

            page += 1
            time.sleep(0.2)

        return all_orders

    def get_companies(self):
        """GET /retail/company/list — список организаций"""
        if not self.token:
            if not self.authenticate():
                return []

        url = f"{self.retail_url}/retail/company/list"
        headers = {"X-SBISAccessToken": self.token}

        try:
            resp = requests.get(url, headers=headers, timeout=30)
            print(f"Companies: {resp.status_code}")
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
                print(f"Companies error: {resp.status_code}, {resp.text[:200]}")
                return []
        except Exception as e:
            print(f"Companies exception: {e}")
            return []

    def get_warehouses(self, company_id):
        """GET /retail/company/warehouses — склады организации"""
        if not self.token:
            if not self.authenticate():
                return []

        url = f"{self.retail_url}/retail/company/warehouses"
        headers = {"X-SBISAccessToken": self.token}
        params = {'companyId': company_id}

        try:
            resp = requests.get(url, headers=headers, params=params, timeout=30)
            print(f"Warehouses: {resp.status_code}")
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
                print(f"Warehouses error: {resp.status_code}, {resp.text[:200]}")
                return []
        except Exception as e:
            print(f"Warehouses exception: {e}")
            return []

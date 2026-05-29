
# ==================== ФИКС RETAIL API URL ====================
# Добавьте в __init__ SbisAPI:
# self.retail_url = "https://api.sbis.ru"

# Замените методы get_sales, get_balances, get_nomenclature_list на эти:

def get_sales(self, point_id=None, date_from=None, date_to=None, page=0, page_size=50):
    """Получить заказы через /retail/order/list (API.SBIS.RU)"""
    if not self.token:
        if not self.authenticate():
            return []

    # Используем retail_url вместо base_url
    retail_url = "https://api.sbis.ru"
    url = f"{retail_url}/retail/order/list"
    headers = {"X-SBISAccessToken": self.token}

    params = {
        'page': page,
        'pageSize': page_size
    }
    if point_id:
        params['pointId'] = point_id
    if date_from:
        # Формат: ГГГГ-ММ-ДД чч:мм:сс
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
        print(f"Sales request: {url}, params={params}, status={resp.status_code}")
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
            print(f"Sales error: {resp.status_code}, body: {resp.text[:200]}")
            return []
    except Exception as e:
        print(f"Sales exception: {e}")
        return []


def get_balances(self, nomenclatures=None, warehouses=None, companies=None, price_list_ids=None):
    """Получить остатки через /retail/nomenclature/balances (API.SBIS.RU)"""
    if not self.token:
        if not self.authenticate():
            return []

    retail_url = "https://api.sbis.ru"
    url = f"{retail_url}/retail/nomenclature/balances"
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
        print(f"Balances request: {url}, status={resp.status_code}")
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
            print(f"Balances error: {resp.status_code}, body: {resp.text[:200]}")
            return []
    except Exception as e:
        print(f"Balances exception: {e}")
        return []


def get_nomenclature_list(self, point_id, price_list_id=None, with_balance=True):
    """Получить номенклатуру через /retail/nomenclature/list (API.SBIS.RU)"""
    if not self.token:
        if not self.authenticate():
            return []

    retail_url = "https://api.sbis.ru"
    url = f"{retail_url}/retail/nomenclature/list"
    headers = {"X-SBISAccessToken": self.token}

    params = {
        'pointId': point_id,
        'withBalance': 'true' if with_balance else 'false'
    }
    if price_list_id:
        params['priceListId'] = price_list_id

    try:
        resp = requests.get(url, headers=headers, params=params, timeout=30)
        print(f"Nomenclature request: {url}, status={resp.status_code}")
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
            print(f"Nomenclature error: {resp.status_code}, body: {resp.text[:200]}")
            return []
    except Exception as e:
        print(f"Nomenclature exception: {e}")
        return []


def get_points(self):
    """Получить список торговых точек /retail/point/list"""
    if not self.token:
        if not self.authenticate():
            return []

    retail_url = "https://api.sbis.ru"
    url = f"{retail_url}/retail/point/list"
    headers = {"X-SBISAccessToken": self.token}

    try:
        resp = requests.get(url, headers=headers, timeout=30)
        print(f"Points request: {url}, status={resp.status_code}")
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
            print(f"Points error: {resp.status_code}, body: {resp.text[:200]}")
            return []
    except Exception as e:
        print(f"Points exception: {e}")
        return []

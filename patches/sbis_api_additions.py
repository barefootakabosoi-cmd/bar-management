    # ==================== ОСТАТКИ (КЕГИ) ====================
    
    def get_balances(self, nomenclatures=None, warehouses=None, companies=None, price_list_ids=None):
        """Получить остатки через /retail/nomenclature/balances"""
        if not self.token:
            if not self.authenticate():
                return []
        
        url = f"{self.base_url}/retail/nomenclature/balances"
        headers = self.get_headers()
        
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
            if resp.status_code == 200:
                return resp.json()
            elif resp.status_code == 401:
                if self.authenticate():
                    resp = requests.get(url, headers=self.get_headers(), params=params, timeout=30)
                    if resp.status_code == 200:
                        return resp.json()
                return []
            else:
                print(f"Balances error: {resp.status_code}")
                return []
        except Exception as e:
            print(f"Balances exception: {e}")
            return []

    def get_nomenclature_list(self, point_id, price_list_id=None, with_balance=True):
        """Получить номенклатуру с остатками через /retail/v2/nomenclature/list"""
        if not self.token:
            if not self.authenticate():
                return []
        
        url = f"{self.base_url}/retail/v2/nomenclature/list"
        headers = self.get_headers()
        
        params = {
            'pointId': point_id,
            'withBalance': 'true' if with_balance else 'false'
        }
        if price_list_id:
            params['priceListId'] = price_list_id
        
        try:
            resp = requests.get(url, headers=headers, params=params, timeout=30)
            if resp.status_code == 200:
                return resp.json()
            elif resp.status_code == 401:
                if self.authenticate():
                    resp = requests.get(url, headers=self.get_headers(), params=params, timeout=30)
                    if resp.status_code == 200:
                        return resp.json()
                return []
            else:
                print(f"Nomenclature list error: {resp.status_code}")
                return []
        except Exception as e:
            print(f"Nomenclature list exception: {e}")
            return []

    # ==================== ПРОДАЖИ ====================
    
    def get_sales(self, point_id=None, date_from=None, date_to=None, page=0, page_size=50):
        """Получить заказы через /retail/order/list"""
        if not self.token:
            if not self.authenticate():
                return []
        
        url = f"{self.base_url}/retail/order/list"
        headers = self.get_headers()
        
        params = {
            'page': page,
            'pageSize': page_size
        }
        if point_id:
            params['pointId'] = point_id
        if date_from:
            params['fromDateTime'] = date_from.isoformat()
        if date_to:
            params['toDateTime'] = date_to.isoformat()
        
        try:
            resp = requests.get(url, headers=headers, params=params, timeout=30)
            if resp.status_code == 200:
                return resp.json()
            elif resp.status_code == 401:
                if self.authenticate():
                    resp = requests.get(url, headers=self.get_headers(), params=params, timeout=30)
                    if resp.status_code == 200:
                        return resp.json()
                return []
            else:
                print(f"Sales error: {resp.status_code}")
                return []
        except Exception as e:
            print(f"Sales exception: {e}")
            return []

    def get_sales_by_period(self, point_id=None, days=7):
        """Продажи за последние N дней со всей пагинацией"""
        from datetime import datetime, timedelta
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
            
            orders = result.get('orders', []) if isinstance(result, dict) else result
            if not orders:
                break
            
            all_orders.extend(orders)
            
            total = result.get('total', 0) if isinstance(result, dict) else len(orders)
            if len(orders) < 100 or len(all_orders) >= total:
                break
            
            page += 1
            time.sleep(0.1)
        
        return all_orders

import re

with open('sbis_api.py', 'r') as f:
    content = f.read()

old_method = '''    def get_balances(self, warehouses=None, companies=None):
        """Получить остатки со СБИС (склад)"""
        if not self.token:
            if not self._get_oauth_token():
                return None

        url = f"{self.api_url}/service/?srv=1"
        
        # Фильтр по складам и компаниям
        filter_params = {}
        if warehouses:
            filter_params["Склады"] = [{"Идентификатор": w} for w in warehouses] if isinstance(warehouses, list) else [{"Идентификатор": warehouses}]
        if companies:
            filter_params["Компании"] = [{"Идентификатор": c} for c in companies] if isinstance(companies, list) else [{"Идентификатор": companies}]

        payload = {
            "jsonrpc": "2.0",
            "method": "СБИС.СписокНоменклатуры",
            "params": {
                "Фильтр": filter_params,
                "Навигация": {
                    "РазмерСтраницы": "100"
                }
            },
            "id": 1
        }

        try:
            resp = requests.post(url, json=payload, headers=self.headers, timeout=60)
            if resp.status_code == 200:
                data = resp.json()
                if "result" in data:
                    result = data["result"]
                    items = result.get("Номенклатура", []) if isinstance(result, dict) else []
                    
                    balances = []
                    for item in items:
                        balances.append({
                            "id": item.get("Идентификатор", ""),
                            "name": item.get("Название", item.get("Наименование", "")),
                            "quantity": self._safe_float(item.get("Остаток", item.get("Количество", 0))),
                            "unit": item.get("Единица", item.get("ЕдИзм", "шт")),
                            "warehouseId": item.get("Склад", {}).get("Идентификатор", "")
                        })
                    return {"balances": balances}
                elif "error" in data:
                    print(f"Balances API error: {data['error']}")
                    return None
            else:
                print(f"Balances request failed: {resp.status_code}")
                return None
        except Exception as e:
            print(f"Balances exception: {e}")
            return None'''

new_method = '''    def get_balances(self, point_id=None, price_list_id=None):
        if not self.token:
            if not self._get_oauth_token():
                return None

        try:
            url = "https://api.sbis.ru/retail/v2/nomenclature/list"
            params = {
                "pointId": point_id or Config.SBIS_POINT_ID,
                "priceListId": price_list_id or Config.SBIS_PRICE_LIST_ID,
                "withBalance": "true",
                "pageSize": "100"
            }
            
            resp = requests.get(url, headers=self.headers, params=params, timeout=60)
            if resp.status_code == 200:
                data = resp.json()
                items = data if isinstance(data, list) else data.get('items', [])
                
                balances = []
                for item in items:
                    balances.append({
                        "id": str(item.get('id', '')),
                        "name": item.get('name', ''),
                        "quantity": float(item.get('balance', 0) or 0),
                        "unit": item.get('unit', 'шт'),
                        "warehouseId": str(item.get('warehouseId', ''))
                    })
                return {"balances": balances}
            else:
                print(f"Balances API error: {resp.status_code} - {resp.text[:200]}")
                return None
        except Exception as e:
            print(f"Balances exception: {e}")
            return None'''

content = content.replace(old_method, new_method)

with open('sbis_api.py', 'w') as f:
    f.write(content)

print("Done!")

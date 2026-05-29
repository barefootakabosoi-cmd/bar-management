
# ==================== УЛУЧШЕННАЯ СИНХРОНИЗАЦИЯ ЗА ГОД ====================

def get_sales_by_period_monthly(self, point_id=None, days=365):
    """
    Продажи за большой период с разбивкой по месяцам.
    Избегает перегрузки API при запросе за год.
    """
    from datetime import datetime, timedelta
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

        print(f"Загрузка: {current_month.strftime('%Y-%m-%d')} → {month_end.strftime('%Y-%m-%d')}")

        page = 0
        month_orders = 0

        while True:
            result = self.get_sales(
                point_id=point_id,
                date_from=current_month,
                date_to=month_end,
                page=page,
                page_size=100
            )

            if not result:
                break

            orders = result.get('orders', []) if isinstance(result, dict) else result
            if not orders:
                break

            all_orders.extend(orders)
            month_orders += len(orders)

            total = result.get('total', 0) if isinstance(result, dict) else len(orders)
            if len(orders) < 100 or month_orders >= total:
                break

            page += 1
            time.sleep(0.2)  # Небольшая задержка между страницами

        print(f"  Месяц загружен: {month_orders} заказов")
        current_month = month_end + timedelta(days=1)

    print(f"Всего загружено: {len(all_orders)} заказов")
    return all_orders


def get_all_nomenclature(self, point_id, price_list_id=None, with_balance=True):
    """
    Вся номенклатура с автопагинацией
    """
    page = 0
    all_items = []

    while True:
        result = self.get_nomenclature_list(
            point_id=point_id,
            price_list_id=price_list_id,
            with_balance=with_balance
        )

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

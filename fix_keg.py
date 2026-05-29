#!/usr/bin/env python3
import sys

file_path = sys.argv[1] if len(sys.argv) > 1 else "sync_retail.py"

with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

# Удаляем блок с keg_liters
old_block = """            # Определяем, является ли товар кегом
            is_keg = False
            keg_liters = None
            if volume:
                keg_liters = float(volume) / 1000  # мл → л
                is_keg = keg_liters >= 10  # Кеги обычно 10л, 20л, 30л

            sb = StockBalance(
                sbis_nomenclature_id=str(item.get('id', '')),
                sbis_warehouse_id=str(self.warehouse_id or ''),
                name=name,
                normalized_name=name.lower() if name else '',
                quantity=float(balance) if balance is not None else 0,
                unit=item.get('unit', 'шт'),
                keg_liters=keg_liters
            )"""

new_block = """            sb = StockBalance(
                sbis_nomenclature_id=str(item.get('id', '')),
                sbis_warehouse_id=str(self.warehouse_id or ''),
                name=name,
                normalized_name=name.lower() if name else '',
                quantity=float(balance) if balance is not None else 0,
                unit=item.get('unit', 'шт')
            )"""

if old_block in content:
    content = content.replace(old_block, new_block)
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"✅ Фикс применён к {file_path}")
else:
    print(f"❌ Блок не найден в {file_path}")
    print("Проверяем, есть ли keg_liters...")
    if "keg_liters" in content:
        print("keg_liters найден, но в другом месте")
        # Пробуем просто удалить keg_liters=keg_liters
        content = content.replace(",
                    keg_liters=keg_liters", "")
        content = content.replace("keg_liters=keg_liters,
                ", "")
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)
        print("✅ keg_liters удалён")
    else:
        print("keg_liters не найден — файл уже исправлен?")

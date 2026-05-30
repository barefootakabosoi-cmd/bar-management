# Патч v8 для твоего репозитория

## Что делает
Добавляет DocOpening, АктСписания, ДокОтгрИсх в твой существующий проект.

## Установка

### Шаг 1: Скопируй патчи
```bash
cd ~/Downloads/bar_management_v7
cp /path/to/patch/patch_sbis_api.py /tmp/
cp /path/to/patch/patch_models.py /tmp/
cp /path/to/patch/patch_app.py /tmp/
cp /path/to/patch/templates/v8_*.html templates/
```

### Шаг 2: Примени патч sbis_api.py
Открой `sbis_api.py`, найди строку `class SbisRetailAPI` и вставь содержимое `patch_sbis_api.py` ПЕРЕД ней.

### Шаг 3: Примени патч models.py
Открой `models.py`, найди `if __name__ == '__main__':` и вставь содержимое `patch_models.py` ПЕРЕД ней.

### Шаг 4: Примени патч app.py
Открой `app.py`, найди `if __name__ == '__main__':` и вставь содержимое `patch_app.py` ПЕРЕД ней.

### Шаг 5: Миграция БД
```bash
flask db migrate -m "add keg_openings writeoffs keg_retail_mapping"
flask db upgrade
```

### Шаг 6: Запуск
```bash
python app.py
```

## Новые URL
- `/v8/openings` — вскрытия кег
- `/v8/writeoffs` — списания
- `/v8/sales-docs` — розничные продажи (ДокОтгрИсх)
- `POST /v8/sync-docs` — синхронизация
- `POST /v8/map-keg` — связать кегу с розливом

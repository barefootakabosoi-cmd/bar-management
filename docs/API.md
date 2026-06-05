# 🔌 API Reference — Bar Management

## Health
```
GET /api/health
Response: {"status":"ok"}
```

## Дашборд
```
GET /
HTML: Dashboard с метриками
```

## Поставщики
```
GET /suppliers          # Список поставщиков
POST /supplier/add      # Добавить поставщика
```

## Прайсы
```
GET /prices             # Текущие цены
POST /upload            # Загрузка Excel/CSV прайса
GET /price/<id>/edit    # Редактировать цену
```

## Рецептуры
```
GET /recipes            # Список рецептов
GET /recipe/<id>        # Детали рецепта
POST /recipe/add        # Добавить рецепт
POST /recipe/<id>/add_item
GET /recipe/<id>/pdf    # PDF (заглушка)
```

## Расходы
```
GET /expenses
POST /expense/add
```

## СБИС
```
GET /sbis               # Список документов
GET /sbis/document/<id>
POST /sbis/sync         # Синхронизация (инкремент/фулл)
```

## Кеги
```
GET /kegs
POST /keg/<tap>/install
POST /keg/<tap>/update
```

## V8 (документы)
```
GET /v8/openings
GET /v8/writeoffs
GET /v8/sales-docs
POST /v8/sync-docs      # Фоновая синхронизация
GET /v8/map-keg         # Маппинг кеги↔розлив
```

## Склад / Продажи
```
GET /stock
POST /stock/sync
GET /sales
POST /sales/sync
```

## Аналитика
```
GET /analytics
```

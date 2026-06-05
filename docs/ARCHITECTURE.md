# 🏗️ Architecture — Bar Management

## Общая схема
```
┌─────────────┐     HTTP      ┌─────────────┐
│   Browser   │ ◄──────────► │   Flask     │
│  (User UI)  │               │   app.py    │
└─────────────┘               └──────┬──────┘
                                     │
                    ┌────────────────┼────────────────┐
                    │                │                │
               ┌────▼────┐     ┌─────▼─────┐   ┌─────▼─────┐
               │ SQLite  │     │  SBIS API │   │  Прайсы   │
               │  (db)   │     │(sbis_api) │   │ (Excel)   │
               └─────────┘     └───────────┘   └───────────┘
```

## Слои
1. **Presentation:** HTML-шаблоны (Jinja2), static (CSS/JS)
2. **Application:** Flask routes, form handling, API endpoints
3. **Domain:** SQLAlchemy models (models.py)
4. **Infrastructure:** SBIS API, file parsers (Excel/PDF), SQLite

## Ключевые модули

### models.py
- `Supplier` / `SupplierOffer` — поставщики и их предложения
- `ActiveSupplierPrice` — текущие цены с историей
- `Recipe` / `RecipeItem` / `RecipeVersion` — рецептуры
- `Expense` / `ExpenseCategory` — расходы
- `Keg` / `KegOpening` / `Writeoff` — кеги и списания
- `SBISDocument` / `SBISDocumentItem` — документы СБИС
- `StockBalance` / `SaleRecord` / `DailySalesSummary` — склад/продажи

### sbis_api.py
- OAuth-аутентификация
- RPC-вызовы (СБИС.ПрочитатьДокумент и др.)
- Парсинг УПД XML, Торг-12
- Розничные методы (retail)

### sbis_retail_api.py
- Наследник SbisAPI
- Point list, order list
- Дублирует часть функционала — требует рефакторинга

## Потоки данных
1. **Прайсы:** Excel/CSV → парсинг → ActiveSupplierPrice → алерты
2. **Рецептуры:** рецепт + цены → себестоимость → маржа
3. **СБИС:** API → документы → номенклатура → остатки
4. **Кеги:** установка → открытие → списание → маппинг розлив

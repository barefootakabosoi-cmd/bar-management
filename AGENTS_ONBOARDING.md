# 🤖 Agent Onboarding — Bar Management

## Кто ты
Ты — AI-агент, работающий над проектом **bar-management** (Flask-приложение для управления пивным баром).

## Где мы
- **Проект:** `~/Downloads/bar_management_v7`
- **Репозиторий:** GitHub (публичный)
- **Технологии:** Flask, SQLAlchemy, SQLite, pandas, SBIS API
- **Python:** 3.13, venv в папке проекта

## Быстрый старт
```bash
cd ~/Downloads/bar_management_v7
make run          # запуск сервера
make health       # проверка health
curl http://127.0.0.1:5000/   # главная страница
```

## Структура проекта
```
bar_management_v7/
├── app.py              # Главный файл Flask (маршруты, вьюхи)
├── models.py           # SQLAlchemy модели
├── sbis_api.py         # Интеграция с СБИС (OAuth, RPC)
├── sbis_retail_api.py  # Розничное API СБИС
├── config.py           # Конфигурация
├── requirements.txt    # Зависимости
├── Makefile            # Команды: make run, make health, make db-init
├── static/             # CSS, JS, изображения
├── templates/          # HTML-шаблоны (Jinja2)
└── docs/               # Документация (ты здесь)
```

## Модули системы
| Модуль | Модели | Маршруты | Статус |
|--------|--------|----------|--------|
| **Поставщики** | Supplier, SupplierOffer | /suppliers, /supplier/add | ✅ |
| **Прайсы** | ActiveSupplierPrice, Alert | /prices, /upload | ✅ |
| **Рецептуры** | Recipe, RecipeItem, RecipeVersion | /recipes, /recipe/<id> | ✅ |
| **Расходы** | ExpenseCategory, Expense | /expenses, /expense/add | ✅ |
| **СБИС** | SBISDocument, SBISDocumentItem | /sbis, /sbis/sync | ✅ |
| **Кеги** | Keg, KegHistory, KegOpening, Writeoff | /kegs, /keg/<tap>/install | ✅ |
| **Склад/Продажи** | StockBalance, SaleRecord, DailySalesSummary | /stock, /sales | ✅ |
| **V8 Синхронизация** | — | /v8/sync-docs, /v8/openings, /v8/writeoffs | ✅ |

## Куда смотреть
- **Задачи:** `TASKS_KANBAN.md`
- **Баги/Тесты:** `TESTS_KANBAN.md`
- **Фичи:** `FEATURES_KANBAN.md`
- **Лог действий:** `AGENTS_LOG.md`
- **Архитектура:** `docs/ARCHITECTURE.md`
- **API:** `docs/API.md`
- **Деплой:** `docs/DEPLOYMENT.md`

## Правила работы
1. **Всегда проверяй** `make health` перед и после изменений
2. **Не коммить** секреты (API-ключи СБИС) — используй `.env`
3. **Логируй** свои действия в `AGENTS_LOG.md`
4. **Обновляй** канбаны при изменении статуса задачи
5. **Тестируй** на `http://127.0.0.1:5000` перед финалом

## Контакты / Контекст
- Владелец: Александр Гурьянов
- Бар: пивной бар (~10 блюд, кеги 30л, бутылки/банки)
- СБИС: касса, склад, документы
- Отчёты по остаткам пива: по четвергам

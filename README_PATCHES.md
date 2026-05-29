# Патчи для Retail API СБИС

## 📁 Файлы

| Файл | Куда копировать | Описание |
|------|-----------------|----------|
| `sync_retail.py` | Корень проекта | CLI-скрипт синхронизации |
| `sbis_api_patch.py` | В конец `sbis_api.py` | Дополнительные методы API |
| `ci.yml` | `.github/workflows/ci.yml` | GitHub Actions |

## 🚀 Быстрый старт

### 1. Добавь методы в sbis_api.py

```bash
cat sbis_api_patch.py >> sbis_api.py
```

### 2. Скопируй sync_retail.py

```bash
cp sync_retail.py /путь/к/проекту/
cd /путь/к/проекту
chmod +x sync_retail.py
```

### 3. Заполни .env

```bash
SBIS_POINT_ID=265          # ID точки продаж
SBIS_WAREHOUSE_ID=123      # ID склада
SBIS_COMPANY_ID=456        # ID компании
SBIS_PRICE_LIST_ID=789     # ID прайс-листа (опционально)
```

### 4. Тестовый запуск

```bash
# Статистика
python sync_retail.py --stats

# Остатки (быстро)
python sync_retail.py --balances

# Продажи за 7 дней
python sync_retail.py --sales --days 7

# Продажи за год (долго, 10-30 мин)
python sync_retail.py --sales --days 365

# Всё сразу
python sync_retail.py --all --days 365
```

## 🔐 GitHub Secrets

Добавь в Settings → Secrets → Actions:

- `SBIS_CLIENT_ID`
- `SBIS_APP_SECRET`
- `SBIS_SECRET_KEY`
- `SBIS_TOKEN`
- `SBIS_POINT_ID`
- `SBIS_WAREHOUSE_ID`
- `SBIS_COMPANY_ID`
- `SBIS_PRICE_LIST_ID`

## ⚠️ Важно

- Первый импорт за год займёт 10-30 минут
- Скрипт разбивает период на месяцы, чтобы не перегружать API
- Между страницами есть задержка 0.2с (не DDoS'им СБИС)
- Логи пишутся в `sync_retail.log`

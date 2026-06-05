# 🚀 Deployment — Bar Management

## Локальный запуск (разработка)
```bash
cd ~/Downloads/bar_management_v7
make run
# или
source venv/bin/activate
FLASK_APP=app.py flask run --host=127.0.0.1 --port=5000
```

## Проверка
```bash
make health
curl http://127.0.0.1:5000/
```

## Зависимости
```bash
make install
# или
pip install -r requirements.txt
```

## База данных
```bash
make db-init
# или
python3 -c "from app import app, db; app.app_context().push(); db.create_all()"
```

## Production (рекомендации)
1. **Не используй** `flask run` в проде
2. Используй **Gunicorn** + **Nginx**
3. Перейди на **PostgreSQL** вместо SQLite
4. Настрой **systemd** unit для автозапуска
5. Настрой **backup** БД

## Переменные окружения
Создай `.env`:
```
SECRET_KEY=your-secret-key
SBIS_CLIENT_ID=...
SBIS_CLIENT_SECRET=...
SBIS_APP_SECRET=...
```

## Docker (запланировано)
```bash
# Будет доступно в будущих версиях
docker build -t bar-management .
docker run -p 5000:5000 bar-management
```

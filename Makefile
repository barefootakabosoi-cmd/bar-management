PYTHON=python3
PIP=pip
VENV=venv
FLASK_APP=app.py

.PHONY: venv install run db-init health run-gunicorn stop-gunicorn status-gunicorn

venv:
	@test -d $(VENV) || $(PYTHON) -m venv $(VENV)
	@. $(VENV)/bin/activate && $(PYTHON) -V && $(PIP) -V

install: venv
	@. $(VENV)/bin/activate && $(PIP) install -r requirements.txt && $(PIP) install gunicorn

run: venv
	@. $(VENV)/bin/activate && FLASK_APP=$(FLASK_APP) flask run --host=127.0.0.1 --port=5000

health:
	@curl -sf http://127.0.0.1:5000/api/health || (echo "healthcheck отсутствует" && curl -s http://127.0.0.1:5000/ | head -5)

db-init: venv
	@. $(VENV)/bin/activate && $(PYTHON) - <<'PY'
from app import app, db
with app.app_context():
    db.create_all()
    print('БД создана')
PY

run-gunicorn: venv
	@. $(VENV)/bin/activate && \ 
	GUNICORN_CMD_ARGS="-c gunicorn.conf.py" \ 
	gunicorn app:app

stop-gunicorn:
	@-lsof -ti tcp:5000 | xargs kill -9 2>/dev/null || true

status-gunicorn:
	@lsof -ni tcp:5000 | grep LISTEN || echo "gunicorn на 5000 не слушает"

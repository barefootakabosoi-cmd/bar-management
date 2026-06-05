.PHONY: venv install run db-init health

PY?=python3
PIP?=pip
VENV=venv
ACT=. $(VENV)/bin/activate;

venv:
	$(PY) -m venv $(VENV)

install: venv
	$(ACT) $(PIP) install -r requirements.txt

run:
	$(ACT) FLASK_APP=app.py flask run --host=127.0.0.1 --port=5000

db-init:
	$(ACT) $(PY) -c "from app import app, db; app.app_context().push(); db.create_all(); print('БД создана')"

health:
	curl -s http://127.0.0.1:5000/api/health || true

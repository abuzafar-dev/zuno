PY := .venv/bin/python

.PHONY: setup db run mig ad test demo

.venv/bin/python:
	uv sync

setup: .venv/bin/python
	test -f .env || cp .env.example .env

db:
	docker compose up -d db redis

mig: .venv/bin/python
	$(PY) manage.py makemigrations
	$(PY) manage.py migrate

ad: .venv/bin/python
	$(PY) manage.py createsuperuser

test: .venv/bin/python
	$(PY) manage.py test

demo: .venv/bin/python
	$(PY) manage.py migrate --noinput
	$(PY) manage.py loaddata apps/fixtures/regions.json apps/fixtures/districts.json
	$(PY) manage.py seed_products
	$(PY) manage.py seed_demo

run: .venv/bin/python
	$(PY) manage.py migrate --noinput
	$(PY) manage.py runserver

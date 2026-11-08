FROM python:3.14-slim AS base
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 UV_LINK_MODE=copy
RUN pip install --no-cache-dir uv
WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project
COPY . .
RUN SECRET_KEY=build-only DEBUG=False .venv/bin/python manage.py collectstatic --noinput
RUN useradd --create-home zuno && mkdir -p media logs && chown -R zuno:zuno /app/media /app/logs
USER zuno
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=4s --start-period=20s CMD .venv/bin/python -c "import urllib.request as u; u.urlopen('http://127.0.0.1:8000/healthz/', timeout=3)"
CMD ["sh", "-c", ".venv/bin/python manage.py migrate --noinput && exec .venv/bin/gunicorn root.wsgi:application -b 0.0.0.0:8000 -w 3 --access-logfile -"]

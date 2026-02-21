# Org Structure API (FastAPI)

API для организационной структуры: подразделения (дерево) и сотрудники.

## Запуск (Docker)

```bash
docker-compose up --build
```

После поднятия контейнеров примените миграции:

```bash
docker-compose exec app alembic upgrade head
```

Swagger: http://localhost:8000/docs

## Переменные окружения

Задаютcя в `docker-compose.yml` (Не вынес в `.env` для облегчения проверки тестового задания):

- `DATABASE_URL` : `postgresql+asyncpg://postgres:postgres@db:5432/org`

## Локальный запуск без Docker

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

export DATABASE_URL="postgresql+asyncpg://postgres:postgres@localhost:5432/org"
alembic upgrade head
uvicorn app.main:app --reload
```

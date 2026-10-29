FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt /app

RUN pip3 install --no-cache-dir -r requirements.txt

COPY alembic.ini /app/alembic.ini
COPY migrations /app/migrations
COPY prompts /app/prompts
COPY src /app/src

EXPOSE 80

CMD ["sh", "-c", "alembic upgrade head && uvicorn api.main:app --app-dir src --host 0.0.0.0 --port 80"]

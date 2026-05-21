FROM python:3.11-slim

WORKDIR /app
ENV PYTHONUNBUFFERED=1

COPY pyproject.toml README.md ./
COPY backend ./backend
COPY ml ./ml
COPY agents ./agents
COPY scripts ./scripts

RUN pip install --no-cache-dir --upgrade pip && pip install --no-cache-dir .

CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]


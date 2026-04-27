FROM python:3.11-slim

WORKDIR /app

RUN pip install uv --no-cache-dir

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen

COPY . .

CMD ["uv", "run", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]

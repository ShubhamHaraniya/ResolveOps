# Backend image (FastAPI app + in-process gateway/MCP servers + RAG). The build context is the
# repository root because the backend imports the top-level `services`, `rag` and `policy` packages.
FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backend ./backend
COPY services ./services
COPY rag ./rag
COPY policy ./policy
COPY evals ./evals

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--app-dir", "backend", "--host", "0.0.0.0", "--port", "8000"]

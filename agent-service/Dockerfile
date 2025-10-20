FROM python:3.11-slim
WORKDIR /app
COPY pyproject.toml ./
RUN pip install --no-cache-dir -U pip setuptools wheel         && pip install --no-cache-dir fastapi uvicorn[standard] pydantic langchain langgraph sqlalchemy psycopg[binary] redis pgvector python-dotenv httpx openai langchain-openai langchain-text-splitters
COPY app ./app
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

FROM python:3.11-slim AS builder
ENV PIP_DISABLE_PIP_VERSION_CHECK=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV VIRTUAL_ENV=/opt/venv
ENV TIKTOKEN_CACHE_DIR=/opt/venv/tiktoken_cache
RUN python -m venv $VIRTUAL_ENV
ENV PATH="$VIRTUAL_ENV/bin:$PATH"
WORKDIR /app

COPY pyproject.toml ./
RUN pip install --no-cache-dir --upgrade pip \
 && pip install --no-cache-dir \
    fastapi==0.115.0 \
    "uvicorn[standard]==0.30.0" \
    pydantic==2.7.0 \
    langchain==0.2.0 \
    langgraph==0.2.0 \
    pyjwt==2.9.0 \
    sqlalchemy==2.0.0 \
    "psycopg[binary]==3.1.20" \
    redis==5.0.0 \
    pgvector==0.2.5 \
    python-dotenv==1.0.1 \
    httpx==0.25.0 \
    openai==1.35.10 \
    langchain-openai==0.1.14 \
    langchain-text-splitters==0.2.4 \
    pypdf==4.2.0 \
    python-multipart==0.0.9 \
    python-docx==1.1.0 \
    beautifulsoup4==4.12.3

# Precalienta el tokenizer de tiktoken para evitar descargas en runtime
RUN python - <<'PY'
import tiktoken
tiktoken.get_encoding('cl100k_base')
print('tiktoken cache primed')
PY


FROM python:3.11-slim AS runtime
ENV VIRTUAL_ENV=/opt/venv
ENV PATH="$VIRTUAL_ENV/bin:$PATH"
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV TIKTOKEN_CACHE_DIR=/opt/venv/tiktoken_cache
WORKDIR /app

COPY --from=builder $VIRTUAL_ENV $VIRTUAL_ENV
COPY app ./app

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

FROM python:3.10-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONUTF8=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# 1) Dependências primeiro (cache de layer)
COPY requirements.txt .
RUN pip install --upgrade pip && \
    pip install -r requirements.txt

# 2) Código da aplicação
COPY . .

# 3) Usuário não-root (segurança)
RUN useradd --create-home --uid 1000 finance && \
    mkdir -p /app/data /app/logs && \
    chown -R finance:finance /app

USER finance

EXPOSE 8050

# Gunicorn com preload: inicializa a app 1x antes do fork dos workers
CMD ["gunicorn", "--preload", "-w", "4", "-b", "0.0.0.0:8050", "wsgi:server"]

FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# System deps. dos2unix protects against the entrypoint being checked out on
# Windows with CRLF line endings, which would make /bin/sh fail with an
# unhelpful "no such file or directory" pointing at the script itself.
RUN apt-get update && apt-get install -y --no-install-recommends \
        curl \
        dos2unix \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

COPY . .

# Normalise line endings on the entrypoint and make it executable.
RUN dos2unix /app/entrypoint.sh && chmod +x /app/entrypoint.sh

EXPOSE 8000

# entrypoint.sh handles: DB wait, migrations, seed (idempotent), uvicorn
ENTRYPOINT ["/app/entrypoint.sh"]

# Multi-Stage, Distroless-inspired Python 3.12 Slim Image (< 80MB)
FROM python:3.12-slim AS builder

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# Final Minimal Runtime Stage
FROM python:3.12-slim

WORKDIR /app

# Run as non-root user for enterprise Kubernetes security
RUN groupadd -g 10001 kubeheal && \
    useradd -u 10001 -g kubeheal -s /bin/sh kubeheal

COPY --from=builder /root/.local /home/kubeheal/.local
COPY app/ ./app/

ENV PATH=/home/kubeheal/.local/bin:$PATH \
    PYTHONUNBUFFERED=1 \
    PORT=8090

USER 10001:10001

EXPOSE 8090

# Non-root healthcheck
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD python3 -c "import urllib.request; urllib.request.urlopen('http://localhost:8090/healthz')"

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8090"]

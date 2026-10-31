# Multi-stage lightweight build for KubeHeal Operator
FROM python:3.11-slim as builder

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# Final runtime image
FROM python:3.11-slim

WORKDIR /app

# Non-root security best practice
RUN useradd -u 10001 -m kubeheal

COPY --from=builder /root/.local /home/kubeheal/.local
COPY . /app

RUN chown -R kubeheal:kubeheal /app

USER kubeheal
ENV PATH=/home/kubeheal/.local/bin:$PATH
ENV PYTHONUNBUFFERED=1

CMD ["python", "main.py"]

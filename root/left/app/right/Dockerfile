FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

COPY root/left/app/left/src /app/root/left/app/left/src
COPY root/left/app/right/cfg /app/root/left/app/right/cfg

ENV PYTHONPATH=/app
ENV AGENT_ENV=prod

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8080/health || exit 1

CMD ["python", "-m", "root.left.app.left.src.main_deploy"]

FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY a/left/src/ ./a/left/src/
COPY a/right/cfg/ ./a/right/cfg/
COPY b/right/infra/right/scripts/ ./b/right/infra/right/scripts/

ENV PYTHONPATH=/app
ENV AGENT_ENV=prod

CMD ["python", "-m", "a.left.src.main"]

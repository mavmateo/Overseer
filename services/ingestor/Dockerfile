FROM python:3.12-slim

WORKDIR /app/services/ingestor
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app/shared/python:/app/services/ingestor

COPY services/ingestor/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt

COPY shared/python /app/shared/python
COPY services/ingestor /app/services/ingestor

CMD ["python", "-m", "app.main"]

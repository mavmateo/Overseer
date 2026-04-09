FROM python:3.12-slim

WORKDIR /app/services/site-forwarder
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app/shared/python:/app/services/site-forwarder

COPY services/site-forwarder/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt

COPY shared/python /app/shared/python
COPY services/site-forwarder /app/services/site-forwarder

CMD ["python", "-m", "app.main"]

FROM python:3.12-slim

WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app/shared/python

COPY services/backend/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt

COPY shared/python /app/shared/python
COPY services/backend /app/services/backend

EXPOSE 8000

CMD ["uvicorn", "services.backend.app.main:app", "--host", "0.0.0.0", "--port", "8000"]

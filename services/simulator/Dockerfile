FROM python:3.12-slim

WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app/shared/python:/app/services/simulator

COPY services/simulator/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt

COPY shared/python /app/shared/python
COPY services/simulator /app/services/simulator

CMD ["python", "services/simulator/app/main.py"]

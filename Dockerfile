FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src/ src/

ENV PYTHONUNBUFFERED=1
ENV SERVICE_ROLE=consumer

CMD ["sh", "-c", "if [ \"$SERVICE_ROLE\" = \"producer\" ]; then python -m src.producer; else python -m src.consumer; fi"]

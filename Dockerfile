FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

WORKDIR /app

RUN apt-get update && apt-get install -y build-essential libpq-dev poppler-utils tesseract-ocr && rm -rf /var/lib/apt/lists/*

COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

COPY . /app

ENV PYTHONPATH=/app
ENV DJANGO_SETTINGS_MODULE=procure_to_pay.settings

CMD ["gunicorn", "procure_to_pay.wsgi:application", "--bind", "0.0.0.0:8000"]
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

WORKDIR /app

# system deps for pillow/pytesseract/pdf processing
RUN apt-get update && apt-get install -y \
    build-essential libpq-dev poppler-utils tesseract-ocr \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

# copy project into container
COPY . /app

ENV PYTHONPATH=/app
ENV DJANGO_SETTINGS_MODULE=core.settings

WORKDIR /app
CMD ["gunicorn", "core.wsgi:application", "--bind", "0.0.0.0:8000"]
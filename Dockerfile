FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    libpq-dev \
 && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

# Copy entire project (adjust if needed)
COPY . .

# Collect static files
RUN python core/manage.py collectstatic --noinput

# Expose port
EXPOSE 8000

# Use Daphne (ASGI server) instead of Gunicorn
CMD ["daphne", "-b", "0.0.0.0", "-p", "8000", "core.asgi:application"]
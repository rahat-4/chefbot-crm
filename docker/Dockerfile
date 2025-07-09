FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Set the working directory inside the container
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc postgresql-client libpq-dev && \
    rm -rf /var/lib/apt/lists/*

# Install pipenv or requirements
COPY ../requirements.txt /app/requirements.txt

# Install python dependencies
RUN pip install --upgrade pip && pip install -r requirements.txt

# Copy the application code into the container
COPY ../core /app

# Expose the port on which the Django application will run
EXPOSE 8000

# # Start the Django development server
# CMD ["gunicorn", "core.wsgi:application", "--bind", "0.0.0.0:8000"]
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]

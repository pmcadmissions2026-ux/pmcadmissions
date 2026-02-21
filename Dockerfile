FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
  && rm -rf /var/lib/apt/lists/*

# Copy project
COPY . /app

# Upgrade pip and install python deps
RUN pip install --upgrade pip
RUN pip install -r requirements.txt

# Create session directory used by Flask-Session
RUN mkdir -p /app/flask_session

# Ensure a `.venv` Python path exists inside the app directory for hosting
# platforms that set start commands to `./.venv/bin/python` (e.g., Railway);
# symlink the system python into `/app/.venv/bin/python` so relative paths work.
RUN mkdir -p /app/.venv/bin && ln -s "$(which python)" /app/.venv/bin/python || true

ENV FLASK_APP=app.py
ENV FLASK_ENV=production
ENV PYTHONUNBUFFERED=1

EXPOSE 5000

# Use the lightweight Waitress start script so we avoid gunicorn/pkg_resources issues
CMD ["python", "start.py"]

# Simple healthcheck to ensure the app is responding
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s CMD curl -f http://localhost:5000/ || exit 1

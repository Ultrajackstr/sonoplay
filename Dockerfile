FROM python:3.12-slim

WORKDIR /app

# Install build dependencies
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        build-essential \
        gcc \
        python3-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies first (better layer caching)
COPY pyproject.toml requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY src/ src/
COPY templates/ templates/
COPY static/ static/
COPY main.py logging_config.py version.py ./
COPY plex/ plex/
COPY dlna/ dlna/
COPY settings/ settings/
COPY utils/ utils/

# Install package in editable mode for development compatibility
RUN pip install --no-cache-dir -e .

ENV HTTP_PORT=32488 CONFIG_PATH=/config
EXPOSE 1910/udp 32412/udp $HTTP_PORT
VOLUME /config

# Use old entry point until full migration
CMD ["python", "-OO", "main.py"]

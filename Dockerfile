FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt ./
RUN apt-get update \
	 && apt-get install -y --no-install-recommends \
		 build-essential \
		 gcc \
		 python3-dev \
	&& rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir -r requirements.txt

ENV HTTP_PORT=32488 CONFIG_PATH=/config
EXPOSE 1910/udp 32412/udp $HTTP_PORT
VOLUME $CONFIG_PATH

COPY . .

CMD ["python", "-OO", "main.py"]

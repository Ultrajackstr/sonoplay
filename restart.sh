#!/bin/bash

clear

sudo docker compose -f docker-compose.yaml down

sudo docker compose -f docker-compose.yaml build --no-cache

sudo docker builder prune -af

sudo docker compose -f docker-compose.yaml up -d

sleep 15

sudo docker compose -f docker-compose.yaml logs -f

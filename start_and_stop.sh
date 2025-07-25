#!/bin/bash

echo "docker container down"

sudo docker compose down

echo "docker container up on port"

sudo docker compose up -d --build

echo "check conitner is running or deploy"

sudo docker ps 
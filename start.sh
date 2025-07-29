#!/bin/bash

echo "docker compose start"

sudo docker compose up -d --build

echo "list out the container"

sudo docker ps -a

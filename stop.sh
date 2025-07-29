#!/bin/bash

echo "docker container down"
sudo docker compose down

if [ $(docker ps -aq | wc -l) == "0" ];
then
    echo "all container is down"

elif [ $(docker ps -aq | wc -l) != "0" ];
then
    echo "down all container focrefully"
    docker rm -f $(docker ps -aq)
    
else
    echo "value not found"
fi



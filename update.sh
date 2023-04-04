#!/bin/bash
sudo docker-compose down -t 5
git pull
sudo docker-compose build --no-cache
sudo docker-compose up -d

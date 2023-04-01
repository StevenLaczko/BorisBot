#!/bin/bash
git pull
sudo docker-compose down -t 5
sudo docker-compose up -d

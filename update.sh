#!/bin/bash
pkill -f borisbot.py
source venv/bin/activate
./requirements.sh
git pull
nohup python3 -u borisbot.py &

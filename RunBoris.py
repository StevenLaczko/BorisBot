import json
import logging
from datetime import datetime
from logging.handlers import RotatingFileHandler

from dotenv import load_dotenv
import os

from src import BorisBot

SETTINGS_FILE = "data/settings.json"

load_dotenv()
TOKEN = os.environ.get("DISCORD_TOKEN")
if __name__ == '__main__':

    with open(SETTINGS_FILE, 'r') as f:
        settings = json.load(f)
    bot = BorisBot.Boris(settings_path=settings)
    bot.run(TOKEN)









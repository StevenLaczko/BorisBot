import logging
from datetime import datetime
from logging.handlers import RotatingFileHandler

from dotenv import load_dotenv
import os

from src import Boris

if __name__ == '__main__':
    load_dotenv()
    TOKEN = os.environ.get("DISCORD_TOKEN")

    bot = Boris.Boris()
    bot.run(TOKEN)









import logging
import json
from datetime import datetime
from logging.handlers import RotatingFileHandler

with open("data/settings.json", 'r') as f:
    settings = json.load(f)

if settings["log_level"] == "info":
    log_level = logging.INFO
elif settings["log_level"] == "debug":
    log_level = logging.DEBUG
else:
    log_level = logging.WARNING
logger = logging.getLogger("main")
logger.setLevel(log_level)
# Create a rotating file handler
handler = RotatingFileHandler(filename=f'logs/boris.log', maxBytes=20000, backupCount=5)
# Set the log level
handler.setLevel(log_level)
# Create a formatter and add it to the handler
formatter = logging.Formatter('[%(asctime)s][%(levelname)s]: %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)

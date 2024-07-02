import logging
import json
import sys
from datetime import datetime
from logging.handlers import RotatingFileHandler

with open("data/settings.json", 'r') as f:
    settings = json.load(f)

log_dict = {
    "info": logging.INFO,
    "error": logging.ERROR,
    "debug": logging.DEBUG,
    "warning": logging.WARNING
}
log_level = log_dict[settings["log_level"]]
logger = logging.getLogger("main")
logger.setLevel(log_level)

# format for log messages
formatter = logging.Formatter('[%(asctime)s][%(levelname)s]: %(message)s')

# print to stdout
stdHandler = logging.StreamHandler(sys.stdout)
stdHandler.setLevel(logging.WARNING)
stdHandler.setFormatter(formatter)
logger.addHandler(stdHandler)

# Create a rotating file handler
handler = RotatingFileHandler(filename=f'logs/boris.log', maxBytes=20000, backupCount=5)
# Set the log level
handler.setLevel(log_level)
# Create a formatter and add it to the handler
handler.setFormatter(formatter)
logger.addHandler(handler)

logger.info(f"Log level is {log_level}")

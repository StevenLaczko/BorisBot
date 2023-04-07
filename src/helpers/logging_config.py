import logging
from datetime import datetime
from logging.handlers import RotatingFileHandler

logger = logging.getLogger("main")
logger.setLevel(logging.INFO)
# Create a rotating file handler
handler = RotatingFileHandler(filename=f'logs/boris.log', maxBytes=10000, backupCount=5)
# Set the log level
handler.setLevel(logging.INFO)
# Create a formatter and add it to the handler
formatter = logging.Formatter('[%(asctime)s][%(levelname)s]: %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)

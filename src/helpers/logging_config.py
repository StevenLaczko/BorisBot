import logging
from datetime import datetime
from logging.handlers import RotatingFileHandler

logger = logging.getLogger("main")
logger.setLevel(logging.INFO)
# Create a rotating file handler
handler = RotatingFileHandler(filename=f'logs/{datetime.now().strftime("%Y-%m-%d_%H-%M-%S")}.log', maxBytes=4096, backupCount=10)
# Set the log level
handler.setLevel(logging.INFO)
# Create a formatter and add it to the handler
formatter = logging.Formatter('[%(asctime)s][%(levelname)s]: %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)

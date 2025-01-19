import logging
from logging.handlers import RotatingFileHandler

# Create a logger
logger = logging.getLogger('app_logger')
logger.setLevel(logging.DEBUG)

# Create a file handler
file_handler = RotatingFileHandler('app.log', maxBytes=1024*1024*10, backupCount=5)
file_handler.setLevel(logging.DEBUG)

# Create a formatter and set it for the file handler
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
file_handler.setFormatter(formatter)

# Add the file handler to the logger
logger.addHandler(file_handler)
import os
import logging
import json

LOG_LEVEL = logging.DEBUG
LOGGER_NAME = "msg_handler_logger"  # make sure this is not the same as the name of the package to avoid conflicts with Flask's own logger
DEBUG = True  # If this is true, then replies get logged to file, rather than hitting the vumi API.

SQLALCHEMY_DATABASE_URI = 'sqlite:///../instance/ford-housing.db'

ONLINE_LAST_MINUTES = 5
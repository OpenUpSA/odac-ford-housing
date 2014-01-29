import os.path as op
import logging

LOG_LEVEL = logging.DEBUG
LOGGER_NAME = "msg_handler_logger"  # make sure this is not the same as the name of the package to avoid conflicts with Flask's own logger
DEBUG = True  # If this is true, then replies get logged to file, rather than hitting the vumi API.

SQLALCHEMY_DATABASE_URI = 'sqlite:///../instance/ford-housing.db'

SECRET_KEY = "AEORJAEONIAEGCBGKMALMAENFXGOAERGN"

ACCESS_TOKEN = '1234567890'
ACCOUNT_KEY = 'b637a80d56f64121af54369e7b027160'
CONVERSATION_KEY = 'f7cf6033331e43b5bf84be6841ef2e65'


ONLINE_LAST_MINUTES = 5
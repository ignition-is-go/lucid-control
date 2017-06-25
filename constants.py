import os
import logging

IS_HEROKU = os.path.isdir("/app/.heroku")

DROPBOX_APP_KEY = os.environ['DROPBOX_APP_KEY']
DROPBOX_APP_SECRET = os.environ['DROPBOX_APP_SECRET']
DROPBOX_APP_FOLDER = os.environ['DROPBOX_APP_FOLDER']
DROPBOX_ACCESS_TOKEN = os.environ['DROPBOX_ACCESS_TOKEN']
XERO_CONSUMER_KEY = os.environ['XERO_CONSUMER_KEY']
XERO_CONSUMER_SECRET = os.environ['XERO_CONSUMER_SECRET']
XERO_API_PRIVATE_KEY = os.environ['XERO_API_PRIVATE_KEY']
LOG_LEVEL = os.environ['LOG_LEVEL']

if LOG_LEVEL.lower()[0] == 'w': LOG_LEVEL_TYPE = logging.WARN
if LOG_LEVEL.lower()[0] == 'e': LOG_LEVEL_TYPE = logging.ERROR
if LOG_LEVEL.lower()[0] == 'i': LOG_LEVEL_TYPE = logging.INFO
if LOG_LEVEL.lower()[0] == 'd': LOG_LEVEL_TYPE = logging.DEBUG
if LOG_LEVEL.lower()[0] == 'c': LOG_LEVEL_TYPE = logging.CRITICAL
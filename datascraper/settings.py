import os
from importlib import import_module

_settings = import_module(os.getenv('SETTINGS_MODULE', 'datascraper.steem_settings'))

DEBUG = os.getenv('DEBUG', '').lower() == 'true'

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

LOG_DIR = os.getenv('LOG_DIR')

if not LOG_DIR:
    LOG_DIR = os.path.join(BASE_DIR, 'logs')
    if not os.path.exists(LOG_DIR):
        os.makedirs(LOG_DIR)

if not os.path.isdir(LOG_DIR) or not os.access(LOG_DIR, os.W_OK):
    raise Exception('Invalid path: check path and access rights.')

IS_STEEM_CHAIN = _settings.IS_STEEM_CHAIN
IS_GOLOS_CHAIN = _settings.IS_GOLOS_CHAIN

NODES = _settings.NODES

MONGO_HOST = _settings.MONGO_HOST
MONGO_PORT = _settings.MONGO_PORT
MONGO_DB_NAME = _settings.MONGO_DB_NAME

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,

    'formatters': {
        'simple': {
            'format': '%(levelname)s\t pid:%(process)d %(asctime)s %(module)s(%(lineno)d): %(message)s'
        }
    },

    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'level': 'DEBUG',
            'formatter': 'simple',
            'stream': 'ext://sys.stdout'
        },

        'info_file_handler': {
            'class': 'logging.handlers.RotatingFileHandler',
            'level': 'INFO',
            'formatter': 'simple',
            'filename': os.path.join(LOG_DIR, 'info.log'),
            'maxBytes': 10485760,
            'backupCount': 20,
            'encoding': "utf8"
        },

        'error_file_handler': {
            'class': 'logging.handlers.RotatingFileHandler',
            'level': 'ERROR',
            'formatter': 'simple',
            'filename': os.path.join(LOG_DIR, 'errors.log'),
            'maxBytes': 10485760,
            'backupCount': 20,
            'encoding': "utf8"
        }
    },

    'loggers': {
        'datascraper': {
            'level': 'ERROR',
            'handlers': ['console'],
            'propagate': False
        }
    },

    'root': {
        'level': 'INFO',
        'handlers': ['console', 'info_file_handler', 'error_file_handler']
    }
}

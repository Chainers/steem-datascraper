import logging.config

from datascraper import settings

logger = logging.getLogger(__name__)

if __name__ == '__main__':
    logging.config.dictConfig(settings.LOGGING)

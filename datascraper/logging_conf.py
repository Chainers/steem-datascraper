import os
from steepcommon import conf

# TODO: move these configurations to settings.py

PROJECT_NAME = 'steepshot-datascraper'
PROJECT_VERSION = '0.1'

# Logging configuration

LOGGING = conf.DEFAULT_LOGGING_CONF

LOGGING['formatters']['logstash']['()'] = 'logstash_async.formatter.LogstashFormatter'
LOGGING['formatters']['logstash']['extra_prefix'] = 'steepshot'
LOGGING['formatters']['logstash']['extra'] = {
    'app_name': PROJECT_NAME,
    'app_version': PROJECT_VERSION
}

LOGGING['formatters']['simple'] = {
    'format': 'pid:%(process)d %(asctime)s (%(threadName)s) %(module)s(%(lineno)d) - %(levelname)s: %(message)s'
}

LOGGING['handlers']['info_file_handler']['backupCount'] = 20
LOGGING['handlers']['error_file_handler']['backupCount'] = 20

LOGGING['root']['level'] = 'DEBUG'
LOGGING['root']['handlers'].append('logstash')


def get_logging_conf(log_path):
    if not log_path or not os.path.isdir(log_path) or not os.access(log_path, os.W_OK):
        log_path = ''

    LOGGING['handlers']['logstash']['database_path'] = os.path.join(log_path, 'logstash.db')
    LOGGING['handlers']['info_file_handler']['filename'] = os.path.join(log_path, 'info.log')
    LOGGING['handlers']['error_file_handler']['filename'] = os.path.join(log_path, 'error.log')
    return LOGGING

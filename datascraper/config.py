import logging.config
import os

import yaml

from datascraper.utils import Object

logger = logging.getLogger(__name__)


class empty: pass  # used in cases where None value is valid


class ConfigError(Exception):
    pass


def remove_last_key(d: dict, *keys, remove_empty=False):
    if not keys:
        return
    if len(keys) == 1:
        d.pop(keys[0], None)
    else:
        remove_last_key(d[keys[0]], *keys[1:], remove_empty=remove_empty)
        if not d[keys[0]] and remove_empty:
            d.pop(keys[0], None)


def get_or_raise(obj: dict, *keys, pop=False, default=empty):
    if not obj or not isinstance(obj, dict):
        raise ConfigError('Failed to get value from empty or non-dict object.')
    value = obj.copy()
    for i, key in enumerate(keys, start=1):
        value = value.get(key, empty)

        item_path = '/'.join(keys[0:i])
        if value is empty:
            if default is not empty:
                return default
            raise ConfigError('Failed to get value on path "%s"' % item_path)
    if pop:
        remove_last_key(obj, *keys, remove_empty=True)
    return value


class Config(object):
    __instance = None

    def __init__(self, config_path):
        self.nodes = []
        self.mongo = None
        self.is_steem_chain = False
        self.is_golos_chain = False

        self._cfg = None
        self._load_conf(config_path)
        self._parse_config()

    @classmethod
    def get_instance(cls, *args, **kwargs):
        if cls.__instance is None:
            cls.__instance = cls(*args, **kwargs)
        return cls.__instance

    def _load_conf(self, path: str):
        if not os.path.isfile(path) or not os.access(path, os.R_OK):
            raise ConfigError('Incorrect config file. Check path and access rights.')
        try:
            with open(path) as f:
                self._cfg = yaml.load(f)
        except OSError as e:
            raise ConfigError('Failed to read config file: %s' % e)
        except yaml.YAMLError as e:
            raise ConfigError('Failed to load YAML-config: %s' % e)

    def _parse_config(self):
        self._parse_logger_section()
        self._parse_datascraper_section()
        self._parse_db_section()

    def _parse_logger_section(self):
        logger_conf = get_or_raise(self._cfg, 'logger', pop=True)
        logging.config.dictConfig(logger_conf)

        logger.info('Logger config has been successfully loaded.')

    def _parse_datascraper_section(self):
        use_web_socket = get_or_raise(self._cfg, 'datascraper', 'use_websocket', pop=True, default=True)
        self.nodes = (
            get_or_raise(self._cfg, 'datascraper', 'nodes', 'http', pop=True),
            get_or_raise(self._cfg, 'datascraper', 'nodes', 'ws', pop=True)
        )[use_web_socket]

        chain_name = get_or_raise(
            self._cfg,
            'datascraper',
            'chain_name',
            pop=True,
        ).lower()

        if chain_name not in ['steem', 'golos']:
            raise ConfigError('Failed to parse chain_type: unknown chain.')
        self.is_steem_chain = chain_name == 'steem'
        self.is_golos_chain = chain_name == 'golos'

    def _parse_db_section(self):
        self.mongo = Object(
            host=get_or_raise(self._cfg, 'db', 'mongo', 'host', pop=True),
            port=get_or_raise(self._cfg, 'db', 'mongo', 'port', pop=True),
            db_name=get_or_raise(self._cfg, 'db', 'mongo', 'db_name', pop=True),
            schema=get_or_raise(self._cfg, 'db', 'mongo', 'schema', pop=True)
        )

import logging.config
import os

import yaml

from datascraper.utils import Object

logger = logging.getLogger(__name__)

_INVALID_VALUE = 0xDEADC0DE  # used in cases where None is valid


class ConfigError(Exception):
    pass


def remove_last_key(d, keys):
    if not keys:
        return
    if len(keys) == 1:
        d.pop(keys[0], None)
    else:
        remove_last_key(d[keys[0]], keys[1:])


def get_or_raise(obj: dict, *keys, pop=False):
    if not obj or not isinstance(obj, dict):
        raise ConfigError('Failed to get value from empty or non-dict object.')
    value = obj.copy()
    for i, key in enumerate(keys, start=1):
        value = value.get(key, _INVALID_VALUE)
        if value == _INVALID_VALUE:
            raise ConfigError('Failed to get value on path "%s"' % '/'.join(keys[0:i]))
    if pop:
        remove_last_key(obj, keys)
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

    def _load_conf(self, path):
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
        datascraper = get_or_raise(self._cfg, 'datascraper', pop=True)

        use_web_socket = datascraper.pop('use_websocket', True)
        nodes_schema = ('http', 'ws')[use_web_socket]

        nodes = get_or_raise(datascraper, 'nodes', nodes_schema)
        self.nodes = nodes

        chain_name = get_or_raise(datascraper, 'chain_name').lower()
        if chain_name == 'steem':
            self.is_steem_chain = True
        elif chain_name == 'golos':
            self.is_golos_chain = True
        else:
            raise ConfigError('Failed to parse config: unsupported chain "%s"' % chain_name)

    def _parse_db_section(self):
        db = get_or_raise(self._cfg, 'db', pop=True)
        mongo = get_or_raise(db, 'mongo')
        self.mongo = Object(
            host=get_or_raise(mongo, 'host'),
            port=get_or_raise(mongo, 'port'),
            db_name=get_or_raise(mongo, 'db_name'),
        )

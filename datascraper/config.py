import os

import yaml
from steepcommon.conf import IS_STEEM_PARAM_NAME, IS_GOLOS_PARAM_NAME

from datascraper.utils import Object


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
        self._nodes = []
        self._mongo = None
        self._logger_conf = None

        self._cfg = None
        self._load_conf(config_path)
        self._parse_config()

    @property
    def nodes(self):
        return self._nodes

    @property
    def logger_conf(self):
        return self._logger_conf

    @property
    def mongo_uri(self):
        auth_data = '{username}{password}{at}'.format(
            username=self._mongo.username if self._mongo.username else '',
            password=':%s' % self._mongo.password if self._mongo.username and self._mongo.password else '',
            at='@' if self._mongo.username else ''
        )

        uri = 'mongodb://{auth}{host}:{port}/{db_name}'.format(
            auth=auth_data,
            host=self._mongo.host,
            port=self._mongo.port,
            db_name=self._mongo.db_name
        )
        return uri

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
        self._logger_conf = logger_conf

    def _parse_datascraper_section(self):
        use_web_socket = get_or_raise(self._cfg, 'datascraper', 'use_websocket', pop=True, default=True)
        self._nodes = (
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

        os.putenv(IS_STEEM_PARAM_NAME, str(chain_name == 'steem'))
        os.putenv(IS_GOLOS_PARAM_NAME, str(chain_name == 'golos'))

    def _parse_db_section(self):
        self._mongo = Object(
            host=get_or_raise(self._cfg, 'db', 'mongo', 'host'),
            port=get_or_raise(self._cfg, 'db', 'mongo', 'port'),
            db_name=get_or_raise(self._cfg, 'db', 'mongo', 'db_name'),
            username=get_or_raise(self._cfg, 'db', 'mongo', 'username', default=None),
            password=get_or_raise(self._cfg, 'db', 'mongo', 'password', default=None),
        )

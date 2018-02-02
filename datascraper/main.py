import argparse
import logging.config

from datascraper.config import Config

logger = logging.getLogger(__name__)


def datascraper():
    parser = argparse.ArgumentParser('datascraper')
    parser.add_argument('-c', '--config', type=str, required=True, help='path to config file')
    args = parser.parse_args()

    cfg = Config.get_instance(args.config)


if __name__ == '__main__':
    datascraper()

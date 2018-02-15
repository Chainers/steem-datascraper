import argparse
import logging.config
import threading

from steepcommon.lib import Steem
from steepcommon.lib.blockchain import Blockchain
from steepcommon.mongo.storage import MongoStorage, Settings

from datascraper.config import Config, ConfigError
from datascraper.scraper import scrape_operations

logger = logging.getLogger(__name__)


def datascraper():
    parser = argparse.ArgumentParser('datascraper')
    parser.add_argument('-c', '--config', type=str, required=True, help='path to config file')
    args = parser.parse_args()

    try:
        cfg = Config.get_instance(args.config)
    except ConfigError as e:
        logger.error('Failed to load config: %s', e)
        raise

    logging.config.dictConfig(cfg.logger_conf)
    logger.info('Logger config has been successfully loaded.')

    steem = Steem(nodes=cfg.nodes)
    blockchain = Blockchain(steemd_instance=steem, mode="irreversible")

    mongo = MongoStorage.get_instance(cfg.mongo_uri)
    settings = Settings(mongo)

    last_block = settings.last_block()
    last_reversed_block = settings.last_reversed_block()

    if last_block == last_reversed_block == 1:
        logger.info('Empty settings found - start scraping from current block in both directions.')
        last_block = last_reversed_block = blockchain.get_current_block_num()
        settings.update_last_block(last_block)
        settings.update_last_reversed_block(last_reversed_block)

    thread = threading.Thread(target=scrape_operations,
                              name='BackwardThread',
                              args=(mongo, cfg, last_reversed_block, True),
                              daemon=True)
    thread.start()

    scrape_operations(mongo, cfg, last_block)


if __name__ == '__main__':
    datascraper()

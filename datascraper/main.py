import argparse
import logging.config
import multiprocessing
import os
import time

from redis import Redis
from redis.exceptions import RedisError
from steepcommon.lib import Steem
from steepcommon.lib.blockchain import Blockchain
from steepcommon.mongo.storage import MongoStorage, Settings

from datascraper.config import Config, ConfigError
from datascraper.scraper import ScrapeProcess
from datascraper.worker import WorkerProcess
from datascraper.logging_conf import get_logging_conf

logger = logging.getLogger(__name__)


# TODO: We can monitor backward process here and terminate it when reach first block of blockchain
# def inspector(redis_objs: dict, backward_process):
def inspector(redis_objs: dict):
    while True:
        for db_name, redis_obj in redis_objs.items():
            # if db_name == 'backward_db' and (not backward_process.is_alive() and redis_obj.llen(db_name) == 0):
            #     backward_process.terminate()
            logger.debug('Number of elements {number} in '
                        '"{db_name}" database.'.format(number=redis_obj.llen(db_name),
                                                       db_name=db_name))
        time.sleep(30)


def block_updater(redis_result_obj: Redis, config: Config):
    # TODO: handle exception
    mongo = MongoStorage(config.mongo_uri)
    settings = Settings(mongo)

    while True:
        last_block = settings.last_block()
        last_reversed_block = settings.last_reversed_block()

        blocks = redis_result_obj.sort('forward_db')
        reversed_blocks = redis_result_obj.sort('backward_db')

        if not blocks and not reversed_blocks:
            time.sleep(3)

        if blocks:
            for block in blocks:
                if int(block) > last_block:
                    settings.update_last_block(int(block))
                    redis_result_obj.lrem('forward_db', block)

        if reversed_blocks:
            for block in reversed_blocks:
                if int(block) < last_reversed_block:
                    settings.update_last_reversed_block(int(block))
                    redis_result_obj.lrem('backward_db', block)


def datascraper():
    parser = argparse.ArgumentParser('datascraper')
    parser.add_argument('-c', '--config', type=str, required=True, help='path to config file')
    args = parser.parse_args()

    try:
        cfg = Config.get_instance(args.config)
    except ConfigError as e:
        logger.error('Failed to load config: %s', e)
        raise

    logging.config.dictConfig(get_logging_conf(cfg.log_path, cfg.chain_name, cfg.server_type))
    logger.info('Logger config has been successfully loaded.')

    steem = Steem(nodes=cfg.nodes)
    blockchain = Blockchain(steemd_instance=steem, mode="irreversible")

    mongo = MongoStorage(cfg.mongo_uri)
    settings = Settings(mongo)

    last_block = settings.last_block()
    last_reversed_block = settings.last_reversed_block()

    if last_block == last_reversed_block == 1:
        logger.info('Empty settings found - start scraping from current block in both directions.')
        last_block = last_reversed_block = blockchain.get_current_block_num()
        settings.update_last_block(last_block)
        settings.update_last_reversed_block(last_reversed_block)

    redis_objs = {}

    try:
        for db_name, index in cfg.redis_databases.items():
            client = Redis(host=cfg.redis_host, port=cfg.redis_port, db=index)
            client.flushdb()
            redis_objs[db_name] = client
    except RedisError as error:
        logger.error(error)
        return

    max_number_workers = min(4, os.cpu_count())

    forward_process = ScrapeProcess(name='ForwardProcess', config=cfg,
                                    redis_obj=redis_objs['forward_db'],
                                    redis_list_name='forward_db',
                                    reversed_mode=False, daemon=False)
    forward_process.start()

    for number in range(max_number_workers):
        worker = WorkerProcess(name='Worker-{}-Forward'.format(number),
                               redis_obj=redis_objs['forward_db'],
                               redis_result_obj=redis_objs['result_db'],
                               redis_list_name='forward_db', config=cfg,
                               reversed_mode=False, daemon=False,
                               polling_freq=0.2)
        worker.start()

    # TODO: Need to implement the ability to perform backward scraping using a few processes
    backward_process = ScrapeProcess(name='BackwardProcess', config=cfg,
                                     redis_obj=redis_objs['backward_db'],
                                     redis_list_name='backward_db',
                                     reversed_mode=True, daemon=False)
    backward_process.start()

    for number in range(max_number_workers):
        worker = WorkerProcess(name='Worker-{}-Backward'.format(number),
                               redis_obj=redis_objs['backward_db'],
                               redis_result_obj=redis_objs['result_db'],
                               redis_list_name='backward_db', config=cfg,
                               reversed_mode=True, daemon=False,
                               polling_freq=1)
        worker.start()

    inspector_process = multiprocessing.Process(target=inspector, name='InspectorProcess',
                                                # args=(redis_objs, backward_process,))
                                                args=(redis_objs,))
    inspector_process.start()

    block_updater_process = multiprocessing.Process(target=block_updater, name='BlockUpdaterProcess',
                                                    args=(redis_objs['result_db'], cfg,))
    block_updater_process.start()


if __name__ == '__main__':
    datascraper()

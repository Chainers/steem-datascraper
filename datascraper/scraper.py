import logging
import multiprocessing
import pickle
from typing import Optional

from redis import Redis
from steepcommon.lib import Steem
from steepcommon.lib.blockchain import Blockchain
from steepcommon.lib.instance import set_shared_steemd_instance
from steepcommon.mongo.storage import MongoStorage, Settings

from datascraper.config import Config
from datascraper.utils import Operation, get_apps_for_operation

logger = logging.getLogger(__name__)


class ScrapeProcess(multiprocessing.Process):
    def __init__(self, name: str, config: Config, redis_list_name: str,
                 redis_obj: Redis, reversed_mode: bool = False,
                 daemon: Optional[bool] = None):
        multiprocessing.Process.__init__(self)
        self.name = name
        self.daemon = daemon
        self.config = config
        self.redis_obj = redis_obj
        self.redis_list_name = redis_list_name
        self.reversed_mode = reversed_mode
        self.steem = Steem(nodes=self.config.nodes)
        self.mongo = None
        set_shared_steemd_instance(self.steem)

    def _check_operation(self, operation):
        op_type = operation['type']
        if op_type in self.config.operation_types:
            if op_type in self.config.transfer_operations:
                return True
            if op_type in self.config.delegate_operations:
                return True
            if op_type in self.config.update_operations:
                return Operation(operation).check_account_auths(self.config.authors_op_update)
            if op_type in self.config.post_operations:
                identifier = Operation(operation).get_identifier()
                parent_identifier = Operation(operation).get_parent_identifier()
                apps_list = get_apps_for_operation(Operation(operation),
                                                   self.mongo,
                                                   self.reversed_mode,
                                                   identifier, parent_identifier)
                if apps_list:
                    return True
        return False

    def _scrape_operations(self, last_block: int):
        # settings = Settings(self.mongo)
        blockchain = Blockchain(steemd_instance=self.steem, mode='irreversible')
        if self.reversed_mode:
            history = blockchain.history(
                start_block=last_block,
                end_block=1
            )
        else:
            history = blockchain.history(
                start_block=last_block
            )

        mode_name = 'reversed' if self.reversed_mode else 'normal'
        logger.info('Fetching operations in {mode} mode, starting with block {block}...'.format(
            mode=mode_name,
            block=last_block
        ))

        block = []
        block_number = last_block

        for operation in history:
            if operation['block_num'] == block_number:
                if operation['type'] in self.config.operation_types:
                    if self._check_operation(operation):
                        block.append(operation)
                continue
            else:
                if block:
                    self.redis_obj.lpush(self.redis_list_name, pickle.dumps(block))

                block.clear()
                block_number = operation['block_num']

                if self._check_operation(operation):
                    block.append(operation)

                if operation['block_num'] != last_block:
                    last_block = operation['block_num']

                    if last_block % 100 == 0:
                        logger.info('mode: %s - #%s: (%s)', mode_name, last_block, blockchain.steem.hostname)

        logger.info('Finished to scrape data in mode "%s".', mode_name)

    def _run_scraper(self):
        settings = Settings(self.mongo)

        last_failed_block = -1

        def get_last_block():
            return settings.last_reversed_block() if self.reversed_mode else settings.last_block()

        for attempt in range(self.config.max_attempts):
            last_block = get_last_block()
            if attempt > 0:
                logger.info('Start scraping blockchain, attempt %s', attempt + 1)
            if attempt and attempt % self.config.skip_freq == 0 and last_failed_block == get_last_block():
                last_block = (last_block - 1) if self.reversed_mode else (last_block + 1)
                logger.info('%s attempt. Skip 1 block.', attempt)
            try:
                self._scrape_operations(last_block)
                break
            except Exception as e:
                logger.exception(
                    'Failed to scraper operations. '
                    'Trying to restart scraper from last synced block in direction "%s": "%s"',
                    'reversed' if self.reversed_mode else 'normal',
                    e
                )
                last_failed_block = get_last_block()
        else:
            logger.error(
                'The maximum number of attempts is reached: %s. '
                'Please ensure that specified nodes is working and re-run scraper.',
                self.config.max_attempts
            )

    def run(self):
        self.mongo = MongoStorage(self.config.mongo_uri)
        self._run_scraper()

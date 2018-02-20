import logging
import threading

from steepcommon.lib import Steem
from steepcommon.lib.blockchain import Blockchain
from steepcommon.lib.instance import set_shared_steemd_instance
from steepcommon.mongo.storage import Settings, MongoStorage

from datascraper.config import Config
from datascraper.methods import upsert_comment, insert_delegate_op
from datascraper.utils import Operation, get_apps_for_operation

logger = logging.getLogger(__name__)


def parse_comment_update_operation(operation: Operation, mongo: MongoStorage, reversed_mode: bool):
    identifier = operation.get_identifier()
    parent_identifier = operation.get_parent_identifier()
    apps_list = get_apps_for_operation(mongo, operation, identifier, parent_identifier, reversed_mode)

    if apps_list:
        upsert_comment(mongo, identifier, apps_list)


def process_operation(operation: Operation, mongo: MongoStorage, reversed_mode: bool):
    op_type = operation['type']

    if op_type in {'author_reward', 'comment', 'vote', 'delete_comment'}:
        identifier = operation.get_identifier()
        if not (reversed_mode and op_type in {'author_reward', 'vote'}):
            thread = threading.Thread(target=parse_comment_update_operation,
                                      name='Thread%s' % identifier,
                                      args=(operation, mongo, reversed_mode),
                                      daemon=False)
            thread.start()
    if op_type in {'delegate_vesting_shares', 'return_vesting_delegation'}:
        insert_delegate_op(mongo, operation)


def scrape_operations(mongo: MongoStorage,
                      config: Config,
                      last_block: int,
                      reversed_mode: bool = False):
    settings = Settings(mongo)
    steem = Steem(nodes=config.nodes)
    set_shared_steemd_instance(steem)
    blockchain = Blockchain(steemd_instance=steem, mode='irreversible')
    if reversed_mode:
        history = blockchain.history(
            start_block=last_block,
            end_block=1
        )
    else:
        history = blockchain.history(
            start_block=last_block
        )

    mode_name = 'reversed' if reversed_mode else 'normal'
    logger.info('Fetching operations in {mode} mode, starting with block {block}...'.format(
        mode=mode_name,
        block=last_block
    ))

    for operation in history:
        process_operation(Operation(operation), mongo, reversed_mode)

        if operation['block_num'] != last_block:
            last_block = operation['block_num']
            if reversed_mode:
                settings.update_last_reversed_block(last_block)
            else:
                settings.update_last_block(last_block)

            if last_block % 100 == 0:
                logger.info('mode: %s - #%s: (%s)', mode_name, last_block, blockchain.steem.hostname)

    logger.info('Finished to scrape data in mode "%s".', mode_name)


def run_scraper(mongo: MongoStorage, config: Config, reversed_mode: bool = False):
    settings = Settings(mongo)

    last_failed_block = -1

    def get_last_block():
        return settings.last_reversed_block() if reversed_mode else settings.last_block()

    for attempt in range(config.max_attempts):
        last_block = get_last_block()
        if attempt > 0:
            logger.info('Start scraping blockchain, attempt %s', attempt + 1)
        if attempt and attempt % config.skip_freq == 0 and last_failed_block == get_last_block():
            last_block = (last_block - 1) if reversed_mode else (last_block + 1)
            logger.info('%s attempt. Skip 1 block.', attempt)
        try:
            scrape_operations(mongo, config, last_block, reversed_mode)
            break
        except Exception as e:
            logger.exception(
                'Failed to scraper operations. Trying to restart scraper from last synced block in direction "%s": "%s"',
                'reversed' if reversed_mode else 'normal',
                e
            )
            last_failed_block = get_last_block()
    else:
        logger.error(
            'The maximum number of attempts is reached: %s. Please ensure that specified nodes is working and re-run scraper.',
            config.max_attempts
        )

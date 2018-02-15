import logging

from bson import json_util
from steepcommon.lib import Steem
from steepcommon.lib.blockchain import Blockchain, json
from steepcommon.lib.instance import set_shared_steemd_instance
from steepcommon.mongo.storage import Settings, MongoStorage

from datascraper.config import Config
from datascraper.methods import upsert_comment, insert_delegate_op
from datascraper.utils import Operation, get_apps_for_operation

logger = logging.getLogger(__name__)


def process_operation(operation: Operation, mongo: MongoStorage, reversed_mode: bool):
    op_type = operation['type']

    identifier = operation.get_identifier()
    parent_identifier = operation.get_parent_identifier()

    apps_list = get_apps_for_operation(mongo, operation, identifier, parent_identifier, reversed_mode)

    if apps_list and op_type in {'author_reward', 'comment', 'vote', 'delete_comment'}:
        logger.info('Update post "%s"', identifier)
        upsert_comment(mongo, identifier, apps_list)
    if op_type in {'delegate_vesting_shares', 'return_vesting_delegation'}:
        serialized_op = json.dumps(operation, default=json_util.default)
        insert_delegate_op(mongo, serialized_op)


def scrape_operations(mongo: MongoStorage,
                      config: Config,
                      last_block: int,
                      reversed_mode: bool = False):
    settings = Settings(mongo)
    steem = Steem(nodes=config.nodes)
    set_shared_steemd_instance(steem)
    blockchain = Blockchain(steemd_instance=steem, mode="irreversible")
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

            # logger.info('#%s: (%s)', last_block, blockchain.steem.hostname)
            if last_block % 100 == 0:
                logger.info('mode: %s - #%s: (%s)', mode_name, last_block, blockchain.steem.hostname)

    logger.info('Finished to scrape data in mode "%s".', mode_name)

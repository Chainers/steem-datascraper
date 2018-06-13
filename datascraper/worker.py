import json
import logging
import multiprocessing
import pickle
import time
from typing import Union

import requests
from cerberus import Validator
from pymongo.errors import DuplicateKeyError, ConnectionFailure
from redis import Redis
from requests import RequestException
from steepcommon.conf import APP_COLLECTIONS
from steepcommon.enums import CollectionType, Application
from steepcommon.lib import Steem
from steepcommon.lib.amount import Amount
from steepcommon.lib.instance import set_shared_steemd_instance
from steepcommon.lib.post import Post
from steepcommon.libbase.exceptions import PostDoesNotExist
from steepcommon.mongo.storage import MongoStorage
from steepcommon.mongo.wrappers import mark_post_as_deleted
from steepcommon.utils import has_images, retry

import datascraper.notification
from datascraper.config import Config
from datascraper.schema import POST_SCHEMA
from datascraper.utils import Operation, get_apps_for_operation

logger = logging.getLogger(__name__)


class WorkerProcess(multiprocessing.Process):
    def __init__(self, name: str, redis_obj: Redis, redis_result_obj: Redis,
                 redis_list_name: str, config: Config, reversed_mode: bool,
                 daemon: bool, polling_freq: Union[int, float]):
        multiprocessing.Process.__init__(self)
        self.name = name
        self.redis_obj = redis_obj
        self.redis_result_obj = redis_result_obj
        self.redis_list_name = redis_list_name
        self.config = config
        self.reversed_mode = reversed_mode
        self.daemon = daemon
        self.polling_freq = polling_freq
        self.steem = Steem(nodes=self.config.nodes)
        self.mongo = None
        set_shared_steemd_instance(self.steem)

    def _insert_delegate_op(self, operation: Operation):
        result = retry(self.mongo.Operations.insert_one, 5, (DuplicateKeyError, ConnectionFailure))(operation)
        if isinstance(result, ConnectionFailure):
            logger.error('Failed to insert operation: %s.', result)

    def _insert_curator(self, operation: Operation):
        amount = Amount(operation['amount'])

        if amount.amount < self.config.curators_payouts['minimal_sum'] or \
                amount.asset not in self.config.curators_payouts['currencies']: return

        data = {
            'username': operation['from'],
            'trx_timestamp': operation['timestamp'],
            'sum': amount.amount,
            'currency': amount.asset,
        }

        result = retry(self.mongo.Curators.insert_one, 5, (DuplicateKeyError, ConnectionFailure))(data)
        if isinstance(result, ConnectionFailure):
            logger.error('Failed to insert operation: %s.', result)

    def _get_post_from_blockchain(self, post_identifier: str) -> Post:
        p = None
        for i in range(5):
            try:
                p = Post(post_identifier)
                break
            except TypeError:
                continue
        if not p:
            raise PostDoesNotExist()
        return p

    def _upsert_comment(self, post_identifier: str, apps: set, post: Post = None, update_root=True):
        if not post or not isinstance(post, Post):
            try:
                post = self._get_post_from_blockchain(post_identifier)
            except PostDoesNotExist:
                post = {'identifier': post_identifier}
                mark_post_as_deleted(post)
                logger.info('Post marked as deleted: "%s"', post_identifier)
                return
            except Exception as e:
                logger.exception('Failed to get post from blockchain: %s', e)
                return

        logger.info('Update post "%s"', post_identifier)
        try:
            for app in apps:
                collections = APP_COLLECTIONS.get(app)
                if not collections:
                    return

                if isinstance(post, Post):
                    if post.is_main_post():

                        v = Validator(POST_SCHEMA, allow_unknown=True)
                        if not v.validate(post):
                            logger.error('Failed to validate post %s. List of errors: %s', post_identifier, v.errors)
                            return

                        validated_post = v.document

                        if app == Application.steepshot and not has_images(validated_post.get('body', '')):
                            mark_post_as_deleted(validated_post)
                            logger.info('Post marked as deleted: "%s"', post_identifier)

                        result = retry(getattr(self.mongo, collections[CollectionType.posts]).update_one, 5,
                                       (DuplicateKeyError, ConnectionFailure))(
                            {'identifier': post_identifier},
                            {'$set': validated_post},
                            upsert=True
                        )
                        if isinstance(result, Exception):
                            logger.error('Failed to insert post: "%s". Error: %s', post_identifier, result)

                        comments = retry(Post.get_all_replies, 5, Exception)(post)
                        if isinstance(comments, Exception):
                            logger.error('Failed to get comments for post: "%s". Error: %s',
                                         post_identifier, comments)
                        else:
                            for comment in comments:
                                self._upsert_comment(comment['identifier'], {app}, comment, update_root=False)
                    else:
                        result = retry(getattr(self.mongo, collections[CollectionType.comments]).update_one, 5,
                                       (DuplicateKeyError, ConnectionFailure))(
                            {'identifier': post_identifier},
                            {'$set': post},
                            upsert=True
                        )
                        if isinstance(result, Exception):
                            logger.error('Failed to insert comment: "%s". Error: %s', post_identifier, result)

                        if update_root:
                            self._upsert_comment(post.root_identifier, {app})
                else:
                    for collection in collections.values():
                        result = retry(getattr(self.mongo, collection).update_one, 5, (DuplicateKeyError, ConnectionFailure))(
                            {'identifier': post_identifier},
                            {'$set': post},
                        )
                        if isinstance(result, Exception):
                            logger.error('Failed to mark post as deleted: "%s". Error: %s', post_identifier, result)
        except AttributeError as e:
            logger.error('Failed to update post: "%s". Error: %s', post_identifier, e)
        except Exception as e:
            logger.exception('Failed to process post "%s". Error: %s', post_identifier, e)

    def _send_notification(self, operation: dict):
        if not self.config.notification.send:
            return

        op_type = operation['type']
        cls_name = self.config.notification.events.get(op_type)
        if cls_name and hasattr(datascraper.notification, cls_name):
            event = getattr(datascraper.notification, cls_name)
            data = event(operation).json()
            try:
                resp = requests.post(self.config.notification.url,
                                     data=json.dumps(data),
                                     headers={
                                         'Content-type': 'application/json',
                                         'Authorization': 'Token %s' % self.config.notification.token
                                     })
                if 200 <= resp.status_code < 400:
                    logger.debug('Notification sent: %s', data)
                else:
                    logger.warning('Failed to send notification: %s. Error: %s', data, resp.content)
            except RequestException as error:
                logger.error('Failed to retrieve data from api: {error}'.format(error=error))

    def _parse_comment_update_operation(self, operation: Operation):
        identifier = operation.get_identifier()
        parent_identifier = operation.get_parent_identifier()
        apps_list = get_apps_for_operation(operation, self.mongo, self.reversed_mode,
                                           identifier, parent_identifier)
        if apps_list:
            self._upsert_comment(identifier, apps_list)

    def _process_block(self, block_obj):
        operations = pickle.loads(block_obj)
        block_number = operations[0]['block_num']
        for operation in operations:
            op_type = operation['type']
            if op_type in self.config.post_operations:
                if not (self.reversed_mode and op_type in {'author_reward', 'vote'}):
                    self._parse_comment_update_operation(Operation(operation))
            if op_type in self.config.delegate_operations:
                self._insert_delegate_op(operation)
            if op_type in self.config.transfer_operations:
                if operation['to'] in self.config.curators_payouts['accounts_for_transfer']:
                    self._insert_curator(operation)

            # notifications
            if not self.reversed_mode and op_type in self.config.notification.events:
                self._send_notification(operation)

        self.redis_result_obj.lpush(self.redis_list_name, int(block_number))

    def run(self):
        logger.debug('Running {}'.format(self.name))
        self.mongo = MongoStorage(self.config.mongo_uri)

        while True:
            if self.redis_obj.llen(self.redis_list_name):
                try:
                    self._process_block(self.redis_obj.rpop(self.redis_list_name))
                except TypeError as error:
                    logger.debug('Queue is empty: {error}.'
                                   'Current size of list {list}: '
                                   '{size}.'.format(error=error,
                                                    size=self.redis_obj.llen(self.redis_list_name),
                                                    list=self.redis_list_name))
            else:
                time.sleep(self.polling_freq)

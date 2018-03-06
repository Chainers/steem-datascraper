import logging

from pymongo.errors import ConnectionFailure
from steepcommon.conf import APP_COLLECTIONS
from steepcommon.enums import CollectionType
from steepcommon.mongo import consts
from steepcommon.mongo.storage import MongoStorage
from steepcommon.utils import get_apps_from_json_metadata, retry

logger = logging.getLogger(__name__)


class Operation(dict):
    def get_identifier(self):
        if self.get('author'):
            return '@%s/%s' % (self.get('author'), self.get('permlink'))

        if self.get('comment_author'):
            return '@%s/%s' % (self.get('comment_author'), self.get('comment_permlink'))

        return ''

    def get_parent_identifier(self):
        if self.get('parent_author'):
            return '@%s/%s' % (
                self.get('parent_author'),
                self.get('parent_permlink')
            )
        return ''


def get_apps_for_operation(operation: Operation,
                           mongo: MongoStorage,
                           reversed_mode: bool,
                           identifier: str = None,
                           parent_identifier: str = None) -> set:
    apps = get_apps_from_json_metadata(operation.get('json_metadata'))

    for app, collections in APP_COLLECTIONS.items():
        posts_name = collections[CollectionType.posts]
        comments_name = collections[CollectionType.comments]

        mongo_posts = getattr(mongo, posts_name, None)
        if mongo_posts:
            if identifier:
                res = retry(mongo_posts.find_one, 3, ConnectionFailure)(
                    {'identifier': identifier, consts.DELETED_FIELD: {'$ne': True}}
                )
                if isinstance(res, Exception):
                    logger.error('Failed to get data from database: %s', res)
                elif res:
                    if not reversed_mode:
                        apps.add(app)
                    # If scraper works in reverse mode that we don't need to update already existing posts
                    continue
            if parent_identifier:
                res = retry(mongo_posts.find_one, 3, ConnectionFailure)(
                    {'identifier': parent_identifier, consts.DELETED_FIELD: {'$ne': True}}
                )
                if isinstance(res, Exception):
                    logger.error('Failed to get data from database: %s', res)
                elif res:
                    if not reversed_mode:
                        apps.add(app)
                    continue

                mongo_comments = getattr(mongo, comments_name, None)
                if mongo_comments:
                    res = retry(mongo_comments.find_one, 3, ConnectionFailure)(
                        {'identifier': parent_identifier}
                    )
                    if isinstance(res, Exception):
                        logger.error('Failed to get data from database: %s', res)
                    elif res:
                        apps.add(app)
                        continue
    return apps

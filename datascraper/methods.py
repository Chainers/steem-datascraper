import logging
from contextlib import suppress

from pymongo.errors import DuplicateKeyError
from steepcommon.conf import APP_COLLECTIONS
from steepcommon.enums import CollectionType
from steepcommon.lib.post import Post
from steepcommon.libbase.exceptions import PostDoesNotExist
from steepcommon.mongo.storage import MongoStorage
from steepcommon.mongo.wrappers import mark_post_as_deleted
from steepcommon.utils import has_images

from datascraper.utils import get_post_from_blockchain, Operation

logger = logging.getLogger(__name__)


def insert_delegate_op(mongo: MongoStorage, operation: Operation):
    with suppress(DuplicateKeyError):
        mongo.Operations.insert_one(operation)


def upsert_comment(mongo: MongoStorage, post_identifier: str, apps: set, post: Post = None):
    if not post or not isinstance(post, Post):
        try:
            post = get_post_from_blockchain(post_identifier)
        except PostDoesNotExist:
            post = {'identifier': post_identifier}
            mark_post_as_deleted(post)
            logger.info('Post marked as deleted: "%s"', post_identifier)
        except Exception as e:
            logger.exception('Failed to get post from blockchain: %s', e)
            return

    logger.debug('Update post "%s"', post_identifier)
    try:
        for app in apps:
            collections = APP_COLLECTIONS.get(app)
            if not collections:
                return

            if isinstance(post, Post):
                if post.is_main_post():
                    if not has_images(post.get('body', '')):
                        mark_post_as_deleted(post)
                        logger.info('Post marked as deleted: "%s"', post_identifier)
                    getattr(mongo, collections[CollectionType.posts]).update_one(
                        {'identifier': post_identifier},
                        {'$set': post},
                        upsert=True
                    )
                    comments = Post.get_all_replies(post)
                    for comment in comments:
                        upsert_comment(mongo, comment['identifier'], {app}, comment)
                else:
                    getattr(mongo, collections[CollectionType.comments]).update_one(
                        {'identifier': post_identifier},
                        {'$set': post},
                        upsert=True
                    )
            else:
                for collection in collections.values():
                    getattr(mongo, collection).update_one(
                        {'identifier': post_identifier},
                        {'$set': post},
                    )
    except AttributeError:
        logger.error('Failed to update post: "%s"', post_identifier)
    except Exception as e:
        logger.exception('Failed to get post from blockchain: %s', e)

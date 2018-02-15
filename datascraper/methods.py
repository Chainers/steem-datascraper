import json
from contextlib import suppress

from bson import json_util
from pymongo.errors import DuplicateKeyError
from steepcommon.conf import APP_COLLECTIONS
from steepcommon.enums import CollectionType
from steepcommon.lib.post import Post
from steepcommon.libbase.exceptions import PostDoesNotExist
from steepcommon.mongo.storage import MongoStorage
from steepcommon.mongo.wrappers import mark_post_as_deleted
from steepcommon.utils import has_images

from datascraper.utils import get_post_from_blockchain


def insert_delegate_op(mongo: MongoStorage, serialized_op: str):
    with suppress(DuplicateKeyError):
        operation = json.loads(serialized_op, object_hook=json_util.object_hook)
        mongo.Operations.insert_one(operation)


def upsert_comment(mongo: MongoStorage, post_identifier: str, apps: set):
    try:
        post = get_post_from_blockchain(post_identifier)
    except PostDoesNotExist:
        post = {'identifier': post_identifier}
        mark_post_as_deleted(post)

    try:
        for app in apps:
            collections = APP_COLLECTIONS.get(app)
            if not collections:
                return

            if isinstance(post, Post):
                if post.is_main_post():
                    # post = post.export()
                    if not has_images(post.get('body', '')):
                        mark_post_as_deleted(post)
                    getattr(mongo, collections[CollectionType.posts]).update_one(
                        {'identifier': post['identifier']},
                        {'$set': post},
                        upsert=True
                    )
                else:
                    # post = post.export()
                    getattr(mongo, collections[CollectionType.comments]).update_one(
                        {'identifier': post['identifier']},
                        {'$set': post},
                        upsert=True
                    )
            else:
                for collection in collections.values():
                    getattr(mongo, collection).update_one(
                        {'identifier': post['identifier']},
                        {'$set': post},
                    )

    except AttributeError:
        pass

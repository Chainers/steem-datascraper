from steepcommon.conf import APP_COLLECTIONS
from steepcommon.enums import CollectionType
from steepcommon.lib.post import Post
from steepcommon.libbase.exceptions import PostDoesNotExist
from steepcommon.mongo import consts
from steepcommon.mongo.storage import MongoStorage
from steepcommon.utils import get_apps_from_json_metadata


class Object(object):
    def __init__(self, **kwargs):
        for kw in kwargs:
            setattr(self, kw, kwargs[kw])


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


def get_apps_for_operation(mongo: MongoStorage,
                           operation: Operation,
                           identifier: str = None,
                           parent_identifier: str = None,
                           reversed_mode: bool = False) -> set:
    apps = get_apps_from_json_metadata(operation.get('json_metadata'))

    for app, collections in APP_COLLECTIONS.items():
        posts_name = collections[CollectionType.posts]
        comments_name = collections[CollectionType.comments]

        mongo_posts = getattr(mongo, posts_name, None)
        if mongo_posts:
            if identifier:
                res = mongo_posts.find_one({'identifier': identifier, consts.DELETED_FIELD: {'$ne': True}})
                if res:
                    if not reversed_mode:
                        apps.add(app)
                    # If scraper works in reverse mode that we don't need to update already existing posts
                    continue
            if parent_identifier:
                res = mongo_posts.find_one({'identifier': parent_identifier, consts.DELETED_FIELD: {'$ne': True}})
                if res:
                    if not reversed_mode:
                        apps.add(app)
                    continue

                mongo_comments = getattr(mongo, comments_name, None)
                if mongo_comments:
                    res = mongo_comments.find_one({'identifier': parent_identifier})
                    if res:
                        apps.add(app)
                        continue
    return apps


def get_post_from_blockchain(post_identifier: str) -> Post:
    # This is workaround for TypeError exception which is raised when blockchain returns None
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

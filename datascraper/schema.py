# How to use schemas:
#
# from cerberus import Validator
#
# v = Validator(POST_SCHEMA, allow_unknown=True)
# is_valid = v.validate(post)  # returns True or False
# validated_data = v.document  # returns validated document or None if post is not valid
# validated_data = v.validated(post)  # validates and returns validated data or None if post is not valid
# errors = v.errors  # an array of errors, if occurred


POST_SCHEMA = {
    'identifier': {'type': 'string', 'empty': False},
    'permlink': {'type': 'string', 'empty': False},
    'max_cashout_time': {'type': 'datetime'},
    'cashout_time': {'type': 'datetime'},
    'percent_steem_dollars': {'type': 'integer', 'coerce': int},
    'title': {'type': 'string', 'empty': False},
    'tags': {'type': 'list',
             'empty': False,
             'schema': {'type': 'string'}},
    'curator_payout_value': {'type': 'dict',
                             'schema': {'asset': {'type': 'string'},
                                        'amount': {'type': 'number'}}},
    'net_rshares': {'type': 'integer', 'coerce': int},
    'parent_permlink': {'type': 'string', 'empty': False},
    'reblogged_by': {'type': 'list',
                     'empty': True,
                     'schema': {'type': 'string'}},
    'body': {'type': 'string', 'empty': False},
    'vote_rshares': {'type': 'integer', 'coerce': int},
    'author_rewards': {'type': 'integer', 'coerce': int},
    'promoted': {'type': 'dict',
                 'schema': {'asset': {'type': 'string'},
                            'amount': {'type': 'number'}}},
    'author_reputation': {'type': 'integer', 'coerce': int},
    'parent_author': {'type': 'string', 'empty': True},
    'category': {'type': 'string', 'empty': False},
    'last_payout': {'type': 'datetime'},
    'net_votes': {'type': 'integer', 'coerce': int},
    'total_vote_weight': {'type': 'integer', 'coerce': int},
    'children': {'type': 'integer', 'coerce': int},
    'beneficiaries': {'type': 'list',
                      'empty': True,
                      'schema': {'type': 'dict',
                                 'schema': {'weight': {'type': 'integer', 'coerce': int},
                                            'account': {'type': 'string'}}}},
    'reward_weight': {'type': 'integer', 'coerce': int},
    'author': {'type': 'string', 'empty': False},
    'community': {'type': 'string', 'empty': True},
    'body_length': {'type': 'integer', 'coerce': int},
    'children_abs_rshares': {'type': 'integer', 'coerce': int},
    'sum_payout_data': {'type': 'dict',
                        'schema': {'asset': {'type': 'string'},
                                   'amount': {'type': 'number'}}},
    'total_pending_payout_value': {'type': 'dict',
                                   'schema': {'asset': {'type': 'string'},
                                              'amount': {'type': 'number'}}},
    'score_trending': {'type': 'number'},
    'score_hot': {'type': 'number'},
    'depth': {'type': 'integer', 'coerce': int},
    'id': {'type': 'integer', 'coerce': int},
    'replies': {'type': 'list', 'empty': True},
    'root_comment': {'type': 'integer', 'coerce': int},
    'root_title': {'type': 'string', 'empty': False},
    'url': {'type': 'string', 'empty': False},
    'created': {'type': 'datetime'},
    'pending_payout_value': {'type': 'dict',
                             'schema': {'asset': {'type': 'string'},
                                        'amount': {'type': 'number'}}},
    'total_payout_value': {'type': 'dict',
                           'schema': {'asset': {'type': 'string'},
                                      'amount': {'type': 'number'}}},
    'active_votes': {'type': 'list',
                     'empty': True,
                     'schema': {'type': 'dict',
                                'schema': {'reputation': {'type': 'integer', 'coerce': int},
                                           'percent': {'type': 'integer', 'coerce': int},
                                           'voter': {'type': 'string'},
                                           'weight': {'type': 'integer', 'coerce': int},
                                           'time': {'type': 'string'},
                                           'rshares': {'type': 'integer', 'coerce': int}}}},
    'last_update': {'type': 'datetime'},
    'json_metadata': {'type': 'dict',
                      'allow_unknown': True,
                      'schema': {'tags': {'type': 'list',
                                          'empty': False,
                                          'schema': {'type': 'string'}},
                                 'app': {'type': 'string'}}},
    'active': {'type': 'datetime'},
    'max_accepted_payout': {'type': 'dict',
                            'schema': {'asset': {'type': 'string'},
                                       'amount': {'type': 'number'}}},
    'abs_rshares': {'type': 'integer', 'coerce': int},
    'allow_votes': {'type': 'boolean'},
    'allow_curation_rewards': {'type': 'boolean'},
    'allow_replies': {'type': 'boolean'}
}

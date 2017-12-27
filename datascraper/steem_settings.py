IS_STEEM_CHAIN = True
IS_GOLOS_CHAIN = False

USE_WEBSOCKET_NODES = True

NODES = [
    'wss://steemd2.steepshot.org',
    'wss://steemd-int.steemit.com',
    'wss://steemd.steemit.com'
] if USE_WEBSOCKET_NODES else [
    'https://steemd2.steepshot.org',
    'https://steemd-int.steemit.com',
    'https://steemd.steemit.com'
]

MONGO_HOST = '127.0.0.1'
MONGO_PORT = 27017
MONGO_DB_NAME = 'SteemData'

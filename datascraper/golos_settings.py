IS_STEEM_CHAIN = False
IS_GOLOS_CHAIN = True

USE_WEBSOCKET_NODES = True

NODES = [
    'wss://golosd.steepshot.org',
    'wss://ws.goldvoice.club',
    'wss://public-ws.golos.io'
] if USE_WEBSOCKET_NODES else [
    'https://golosd.steepshot.org',
    'https://ws.goldvoice.club',
    'https://public-ws.golos.io'
]

MONGO_HOST = '127.0.0.1'
MONGO_PORT = 27017
MONGO_DB_NAME = 'GolosData'

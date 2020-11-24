#!/usr/bin/env python3

from cryptobot import config, logger

import requests
import requests.auth
import datetime
import base64
import json
import hmac
import hashlib
import time

class CoinbaseExchangeAuth(requests.auth.AuthBase):
    def __init__(self, api_key, secret_key, passphrase):
        self.api_key = api_key
        self.secret_key = secret_key
        self.passphrase = passphrase

    def __call__(self, request):
        timestamp = str(time.time())
        message = timestamp + request.method + request.path_url + (request.body or '')
        hmac_key = base64.b64decode(self.secret_key)
        signature = hmac.new(hmac_key, message.encode(), hashlib.sha256)
        signature_b64 = base64.b64encode(signature.digest()).decode().rstrip('\n')

        request.headers.update({
            'CB-ACCESS-SIGN': signature_b64,
            'CB-ACCESS-TIMESTAMP': timestamp,
            'CB-ACCESS-KEY': self.api_key,
            'CB-ACCESS-PASSPHRASE': self.passphrase,
            'Content-Type': 'application/json'
        })
        return request

assert config.get('coinbase.api-key')
assert config.get('coinbase.api-secret')
assert config.get('coinbase.api-pw')

API_KEY = config.get('coinbase.api-key')
API_SECRET = config.get('coinbase.api-secret')
API_PW = config.get('coinbase.api-pw')
API_DELAY = float(config.get('coinbase.api-delay', 0.5)) # how long to wait after every request to prevent rate limiting

auth = CoinbaseExchangeAuth(API_KEY, API_SECRET, API_PW)

BASE_URL = 'https://api.pro.coinbase.com'
SANDBOX_URL = 'https://api-public.sandbox.pro.coinbase.com'


# returns the coin and USD wallet balances in a dict
def coinbase_accounts() -> dict:
    logger.debug('Fetching Coinbase account balance...')
    results = {x['currency']: x for x in requests.get(BASE_URL + '/accounts', auth=auth).json() if x['currency'] in ['USD', config.get('bot.coin')]}
    time.sleep(API_DELAY)
    return results


# returns the coin price at a given unix timestamp in history
def get_historic_price(unixts: int) -> float:
    product_id = config.get('bot.coin') + '-USD'
    logger.debug(f'Fetching {product_id} price at unix timestamp %d...' % unixts)

    # fetch timestamp data
    encode_ts = lambda ts: datetime.datetime.utcfromtimestamp(ts).isoformat() # ISO 8601
    start = encode_ts(unixts)
    end = encode_ts(unixts+60)
    r = requests.get(BASE_URL + f'/products/{product_id}/candles?start={start}&end={end}&granularity=60', auth=auth).json()

    # sanity checks against price data returned
    assert r, 'No price history for unixts %d!' % unixts
    r = r[-1] # pull the last from the list of candles
    assert abs(unixts - r[0]) < 60, 'Price value returned is for a timestamp that is too far away from the requested timestamp (>60sec)! Unixts: %d, r[0]: %d' % (unixts, r[0])

    open_price = r[3]
    volume = r[5]

    time.sleep(API_DELAY)
    return float(open_price)


# get the current price of the selected coin
def get_current_price() -> float:
    product_id = config.get('bot.coin') + '-USD'
    logger.debug(f'Fetching current {product_id} price...')
    result = requests.get(BASE_URL + f'/products/{product_id}/ticker').json()['price']
    time.sleep(API_DELAY)
    return float(result)

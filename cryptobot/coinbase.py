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
        message = timestamp.encode() + request.method.encode() + request.path_url.encode() + (request.body or b'')
        hmac_key = base64.b64decode(self.secret_key)
        signature = hmac.new(hmac_key, message, hashlib.sha256)
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





#!/usr/bin/env python3

from cryptobot import config, logger, database

import requests
import requests.auth
import datetime
import base64
import json
import hmac
import hashlib
import time

import cryptobot.coinbase


auth = cryptobot.coinbase.auth
BASE_URL = cryptobot.coinbase.BASE_URL
API_DELAY = cryptobot.coinbase.API_DELAY

CACHE_TIMEOUT = 10
current_price = None
_current_price_cache_time = None


# returns the coin price at a given unix timestamp in history
def get_historic_price(unixts: int) -> float: # TODO: implement caching
    product_id = config.get('bot.coin') + '-USD'
    logger.debug(f'Fetching {product_id} price at unix timestamp %d...' % unixts)

    # check if we already have the price history data point
    unixts = int(unixts)
    c = database.database()
    r = c.execute((
        # XXX: should we ORDER BY so it's `current` before `historic` for source?
        'SELECT `unixts`, `v` AS `spot` FROM ('
            # select the closest two values to what we're looking for
            'SELECT MIN(`unixts`) as `v`, `spot`, `product_id` FROM `price_history` WHERE `product_id`=? AND `unixts` >= ?'
            'UNION SELECT MAX(`unixts`) as `v`, `spot`, `product_id` FROM `price_history` WHERE `product_id`=? AND `unixts` <= ?'
        # then select only values within 5 minutes of what we want
        ') WHERE `unixts` NOT NULL AND ABS(? - `unixts`) <= (60 * 5) ORDER BY ABS(? - `unixts`) ASC LIMIT 1;'
    ), (product_id, unixts, product_id, unixts, unixts, unixts))
    row = r.fetchone()
    c.close()

    # check if we found one in the db
    if row:
        found_unixts, price = row
        logger.debug('Requested unixts=%d, found cached historic price %.2f USD / coin with unixts=%d in database' % (unixts, price, found_unixts))
        return price

    # fetch timestamp data
    encode_ts = lambda ts: datetime.datetime.utcfromtimestamp(ts).isoformat() # ISO 8601
    start = encode_ts(unixts)
    end = encode_ts(unixts+60)
    r = requests.get(BASE_URL + f'/products/{product_id}/candles?start={start}&end={end}&granularity=60', auth=auth).json()
    time.sleep(API_DELAY)

    # sanity checks against price data returned
    assert r, 'No price history for unixts %d! r=%s' % (unixts, repr(r))
    r = r[-1] # pull the last from the list of candles (which has the open price @ `unixts`
    assert abs(unixts - r[0]) < 60, 'Price value returned is for a timestamp that is too far away from the requested timestamp (>60sec)! Unixts: %d, r[0]: %d' % (unixts, r[0])

    open_price = float(r[3])
    volume = r[5]

    # store price history in db
    c = database.database()
    c.execute('INSERT INTO `price_history` (`unixts`, `product_id`, `spot`, `source`) VALUES (?, ?, ?, \'historic\')', (int(unixts), product_id, open_price))
    database.commit()
    c.close()

    return open_price


# get the current price of the selected coin
def get_current_price(use_cache: bool=True, product_id_override: str=None, commit: bool=True) -> float:
    global current_price, _current_price_cache_time
    cur_time = time.time()

    product_id = config.get('bot.coin') + '-USD' # XXX: changing this mid-program could potentially mess up cached price since it wouldn't update if cached

    # XXX/HACK: this is for the `$ cryptobot check-price` command
    if product_id_override:
        product_id = product_id_override

    if (not use_cache) or (not _current_price_cache_time or _current_price_cache_time + CACHE_TIMEOUT < cur_time):
        logger.debug(f'Fetching current {product_id} price...')
        result = requests.get(BASE_URL + f'/products/{product_id}/ticker').json()
        time.sleep(API_DELAY)

        spot_price = float(result['price'])
        bid_price = float(result['bid'])
        ask_price = float(result['ask'])
        volume = float(result['volume'])

        # cache price
        current_price = spot_price
        _current_price_cache_time = cur_time

        # store price history in db
        c = database.database()
        c.execute('INSERT INTO `price_history` (`unixts`, `product_id`, `spot`, `bid`, `ask`, `volume`, `source`) VALUES (?, ?, ?, ?, ?, ?, \'current\')', (int(cur_time), product_id, spot_price, bid_price, ask_price, volume))
        if commit:
            database.commit()
        c.close()

    return current_price


# get the percent difference from back then until now
def get_percent_change(unixts: int, use_cache: bool=True) -> float:
    current_price = get_current_price(use_cache=use_cache)
    historic_price = get_historic_price(unixts)

    difference = current_price - historic_price
    return difference / historic_price

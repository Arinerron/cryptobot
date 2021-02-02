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


CURRENT_TIME = 0 # unix timestamp, current simulated time

_price_cache = dict()


# get the current time, but simulated
def get_time() -> float:
    return float(CURRENT_TIME)


# returns the coin price at a given unix timestamp in history
def get_historic_price(unixts: int, product_id_override: str=None) -> float:
    global _price_cache

    product_id = product_id_override or (config.get('bot.coin') + '-USD')

    # cache the historic prices to minimize queries
    if product_id not in _price_cache:
        _price_cache[product_id] = dict()
    if unixts in _price_cache[product_id]:
        return _price_cache[product_id][unixts]

    # check if we already have the price history data point
    unixts = int(unixts)
    c = database.database(use_file=database._REG_DB, read_only=True)
    r = c.execute((
        # XXX: should we ORDER BY so it's `current` before `historic` for source?
        'SELECT `v` AS `unixts`, `spot` FROM ('
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
        #logger.debug('Requested unixts=%d, found cached historic price %.2f USD / coin with unixts=%d in database' % (unixts, price, found_unixts))
        _price_cache[product_id][unixts] = price
        return price

    raise ValueError('Could not find price data for price: ' + str(unixts))


# get the current price of the selected coin
# NOTE: we just ignore `use_cache` and `commit`
def get_current_price(use_cache: bool=True, product_id_override: str=None, commit: bool=True) -> float:
    return get_historic_price(int(get_time()), product_id_override=product_id_override)


# get the percent difference from back then until now
def get_percent_change(unixts: int, use_cache: bool=True) -> float:
    current_price = get_current_price(use_cache=use_cache)
    historic_price = get_historic_price(unixts)

    difference = current_price - historic_price
    return difference / historic_price

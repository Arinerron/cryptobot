#!/usr/bin/env python3

from cryptobot import config, logger, database

import requests
import time
import json

import cryptobot.coinbase

auth = cryptobot.coinbase.auth
BASE_URL = cryptobot.coinbase.BASE_URL
API_DELAY = cryptobot.coinbase.API_DELAY

CACHE_TIMEOUT = 10

balance = None
_balance_cache_time = None


# {"ETH": {"balance": ...}, "USD": {"balance": ...}}
# get the user's balance
def get_balance(use_cache: bool=True) -> dict:
    global balance, _balance_cache_time
    cur_time = time.time()

    if (not use_cache) or (not _balance_cache_time or _balance_cache_time + CACHE_TIMEOUT < cur_time):
        # cache expired, refetch
        logger.debug('Fetching Coinbase account balance...')

        # https://docs.pro.coinbase.com/#list-accounts
        results = {x['currency']: x for x in requests.get(BASE_URL + '/accounts', auth=auth).json() if x['currency'] in ['USD', config.get('bot.coin')]}
        time.sleep(API_DELAY)

        # cache results
        balance = results
        _balance_cache_time = cur_time

        # insert into db for stats purposes
        usd_balance = float(balance['USD']['balance'])
        coin_balance = float(balance[config.get('bot.coin')]['balance'])
        c = database.database()
        c.execute('INSERT INTO `portfolio_history` (`product_id`, `coin`, `usd`) VALUES (?, ?, ?)', (config.get('bot.coin') + '-USD', coin_balance, usd_balance))
        database.commit()
        c.close()

    return balance


# place a market order
def order(txn_side: str, txn_size: float, txn_funds: float):
    coin = config.get('bot.coin')
    assert coin != None, 'You must configure a specific coin'
    product_id = f'{coin}-USD'

    # make sure transaction settings are valid
    assert txn_side in ['buy', 'sell'], 'Invalid transaction side.'
    assert (txn_size == 0) or (txn_funds == 0), 'Either size or funds must be 0.'
    assert not (txn_size ==0 and txn_funds == 0), 'Size and funds cannot both be 0.'

    parameters = {
        'type': 'market',
        'side': txn_side, # buy or sell
        'product_id': product_id
    }

    if txn_size != 0:
        # desired amount in base currency
        parameters['size'] = txn_size
    if txn_funds != 0:
        # desired amount of quote currency to use
        parameters['funds'] = txn_funds

    logger.debug(f'Placing {txn_side.upper()} order :: {product_id} :: %.2f {coin} || %.2f USD...' % (txn_size, txn_funds))

    if not config.get('coinbase.enable-trades', True):
        logger.warning('Nevermind! Coinbase transactions are disabled. Exiting...')
        return False

    # https://docs.pro.coinbase.com/#place-a-new-order
    results = requests.post(BASE_URL + '/orders', json=parameters, auth=auth).json()
    logger.debug('RESULTS 2: ' + str(results) + ' type ' + str(type(results)) + 'dir' + str(dir(results)))
    assert results.get('message') != 'Forbidden', 'Permission to trade denied, check API key permissions.'
    if (message := results.get('message')):
        raise ValueError('Failed to make transaction: ' + str(message))
    time.sleep(API_DELAY)

    # store order in db
    # Example `results`: {"id": "3fa3d9c4-33a8-4c5c-96c8-643cf33d4262", "size": "5", "product_id": "ETH-USD", "side": "buy", "stp": "dc", "funds": "199.00507629", "type": "market", "post_only": false, "created_at": "2020-11-24T05:27:13.272383Z", "fill_fees": "0", "filled_size": "0", "executed_value": "0", "status": "pending", "settled": false}
    logger.debug('Placed order. Results:' + str(results))
    c = database.database()
    c.execute('INSERT INTO `orders` (`product_id`, `order_id`, `side`, `size`, `funds`) VALUES (?, ?, ?, ?, ?)', (product_id, results['id'], txn_side, float(txn_size), float(txn_funds)))
    database.commit()
    c.close()

    return results

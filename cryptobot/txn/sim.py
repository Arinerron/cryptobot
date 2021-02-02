#!/usr/bin/env python3

from cryptobot import config, logger, database, analysis

import requests
import time
import datetime
import json


ACCOUNTS = dict()


def get_historic_balance(unixts: int, product_id_override: str=None) -> tuple: # (coin, USD) or None
    # NOTE: this shouldn't be used anywhere important, just a placeholder
    #   because `scripts/cryptobot` uses it and I want to make sure nothing
    #   gets messed up.
    raise NotImplementedError()


# {"ETH": {"balance": ...}, "USD": {"balance": ...}}
# get the user's balance
def get_balance(use_cache: bool=True) -> dict:
    # insert into db for stats purposes
    balance = ACCOUNTS
    usd_balance = float(balance['USD']['balance'])
    coin_balance = float(balance[config.get('bot.coin')]['balance'])
    c = database.database()
    c.execute('INSERT INTO `portfolio_history` (`ts`, `product_id`, `coin`, `usd`) VALUES (?, ?, ?, ?)', (datetime.datetime.fromtimestamp(analysis.history.get_time()), config.get('bot.coin') + '-USD', coin_balance, usd_balance))
    database.commit()
    c.close()
    return balance


def order(txn_side: str, txn_size: float, txn_funds: float):
    coin, usd = config.get('bot.coin'), 'USD'
    product_id = f'{coin}-{usd}'

    calc_with_fees = lambda x: 1.005 * x

    get_balance_of = lambda t: get_balance().get(t, {}).get('balance', 0.00)
    assert not (txn_size and txn_funds), 'txn_size and txn_funds cannot both be non-zero at the same time'
    assert not (txn_size == 0 and txn_funds == 0), 'txn_size and txn_funds cannot both be 0'
    assert txn_size >= 0 and txn_funds >= 0, 'txn_size and txn_funds cannot be negative'
    assert txn_size <= get_balance_of(coin), 'txn_size cannot be greater than coin balance'
    assert txn_funds <= get_balance_of(usd), 'txn_funds cannot be greater than usd balance'
    assert txn_side in ['buy', 'sell'], 'invalid txn_side; must be buy or sell'

    logger.debug(f'Placing {txn_side.upper()} order :: {product_id} :: %.2f {coin} || %.2f USD...' % (txn_size, txn_funds))

    current_price = analysis.history.get_current_price()

    c = database.database()
    c.execute('INSERT INTO `orders` (`ts`, `product_id`, `order_id`, `side`, `size`, `funds`) VALUES (?, ?, ?, ?, ?, ?)', (datetime.datetime.fromtimestamp(analysis.history.get_time()), product_id, 'fake', txn_side, float(txn_size), float(txn_funds)))
    database.commit()
    c.close()

    if txn_side == 'buy':
        # TODO: calculate fees, and the market v.s. buy/sell prices
        assert txn_funds <= get_balance_of(usd), 'txn_funds cannot be greater than usd balance' # keep this because we need to calc for fees too
        txn_size = txn_funds / current_price
        get_balance()[coin]['balance'] += txn_size
        get_balance()[usd]['balance'] -= calc_with_fees(txn_funds) # XXX: doesn't check if fees will make balance negative
        get_balance()[coin]['available'] += txn_size
        get_balance()[usd]['available'] -= calc_with_fees(txn_funds) # XXX: doesn't check if fees will make balance negative
    elif txn_side == 'sell':
        # TODO: calculate fees, and the market v.s. buy/sell prices
        assert txn_size <= get_balance_of(coin), 'txn_size cannot be greater than coin balance' # keep this because we need to calc for fees too
        txn_funds = txn_size * current_price
        get_balance()[coin]['balance'] -= calc_with_fees(txn_size) # XXX: doesn't check if fees will make balance negative
        get_balance()[usd]['balance'] += txn_funds
        get_balance()[coin]['available'] -= calc_with_fees(txn_size) # XXX: doesn't check if fees will make balance negative
        get_balance()[usd]['available'] += txn_funds

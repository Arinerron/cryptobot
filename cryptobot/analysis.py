#!/usr/bin/env python3

from cryptobot import config, logger, database

import math
import time
import datetime

import cryptobot


# pick which harness to use from the config
history = {
    'coinbase': cryptobot.history.coinbase,
    'sim': cryptobot.history.sim
}.get(config.get('bot.history-harness', 'coinbase'))
assert history != None, 'Invalid history harness specified'

txn = {
    'coinbase': cryptobot.txn.coinbase,
    'sim': cryptobot.txn.sim
}.get(config.get('bot.txn-harness', 'coinbase'))
assert txn != None, 'Invalid transaction (txn) harness specified'

# we want to weigh different price changes over time 
WEIGHTS = {
    # hours ago: weight multiplier
    1: 0.4, # 1 hour ago
    1 * 24: 0.3, # 1 day ago
    1 * 24 * 7: 0.2, # 1 week ago
    1 * 24 * 7 * 4: 0.1 # 1 month ago
    
    # NOTE: we don't do "1 year ago" or anything longer because cryptocurrency 
    #   bubbles tend to happen every year. We want the price direction to be
    #   at least somewhat consistent (though we can never predict this) for 
    #   all of the weighted percentges. The best we can do is keep the 
    #   percentages within the average bubble timeframe.
}

# other price settings
VOLATILITY = config.get('bot.volatility', 2500)


################################################################################
# Useful functions, not intended for export
################################################################################


# returns -1 or 1 depending on whether it's a positive or negative number
def sign(value: float) -> int:
    return abs(value) / value


# normalize movement score by forcing it to be between certain values (using a curve)
def curve(value: float, max_score: int) -> float:
    return sign(value) * max_score * (1 + (-1 / math.sqrt(abs(value) + 1)))


################################################################################
# Bot's main market analysis functions
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# - "Movement score" is a number from 0 to 10, where anything above 5 means bull 
#   market, and anything below 5 means bear market.
# - "Movement change score" is a score from 0 to 1 that represents how intense a
#   bull/bear market is by figuring in past movement scores.
# - "Volatility" is a setting that specifies how easily the bot should take 
#   decisions to buy/sell. The higher the number, the more trades the bot will
#   do, and vice versa. Generally, a higher volatliity number is better. Idk why
# - "Market direction" is a number that is either -1 or 1 that means bear or 
#   bull market, respectively.
################################################################################


# get portfolio value in USD
# NOTE: must be in analysis.py because txn handler doesn't know which history handler to use
# XXX: this function isn't used anywhere, delete it?
def get_portfolio_value(use_cache: bool=True) -> float:
    current_price = history.get_current_price(use_cache=use_cache)
    balance = txn.get_balance(use_cache=use_cache)
    usd_balance = balance['USD']['balance']
    coin_balance = balance[config.get('bot.coin')]['balance']
    return usd_balance + (coin_balance * current_price)


# get the minimum coin/usd trade size to allow
def get_minimum_trade_size() -> tuple:
    # (min coin, min usd)
    return config.get('bot.min-trade.coin', 0.1), config.get('bot.min-trade.usd', 50)


# calculate the price movement score
def get_movement_score() -> float:
    raw_score = 0
    cur_time = time.time()

    for period, weight in WEIGHTS.items():
        unixts = cur_time - (period * 60 * 60)
        change = history.get_percent_change(unixts)
        assert change != None, "Not enough price history to calculate score!"
        raw_score += weight * change

    score = curve(raw_score, len(WEIGHTS)) # XXX: len()+1?
    return score


# check the market for new movements and make actions if necessary (main function)
def analyze_market():
    movement_score = get_movement_score()
    last_movement_score = None # TODO
    
    c = database.database()
    r = c.execute('SELECT datetime(`ts`, \'localtime\'), `score` FROM `movement_score_history` WHERE `product_id`=? ORDER BY id DESC LIMIT 1', (config.get('bot.coin') + '-USD',))
    row = r.fetchone()
    c.close()
    
    # if there was result / this is not the first run
    if row:
        # ensure it's been at least an hour (about) since the last run
        ts, last_movement_score = row
        if time.time() - datetime.datetime.strptime(ts, '%Y-%m-%d %H:%M:%S').timestamp() < ((60 * 60) - 10):
            logger.warning('Not running analysis as it has already run within the past hour.')
            return
    
    # store the movement score in the db for future fetching
    c = database.database()
    c.execute('INSERT INTO `movement_score_history` (`product_id`, `score`) VALUES (?, ?)', (config.get('bot.coin') + '-USD', movement_score))
    database.commit()
    c.close()
    
    # check if first run
    if last_movement_score == None:
        logger.warning('Skipping analysis as this is the first run.')
        return
    
    assert False, 'no going past here!'
    
    # find the change in movement scores and normlize to 0 to 1 (instead of 0 to len(WEIGHTS)*2)
    movement_change_score = abs(movement_score - last_movement_score) / (len(WEIGHTS) * 2)
    minimum_movement_change_score_to_take_action = 1 / (2 * VOLATILITY)

    # check if we should take action
    if movement_change_score >= minimum_movement_change_score_to_take_action:
        logger.debug('Movement change score %.2f is large enough to justify taking action.' % movement_change_score)
        
        # get the current balance
        balance = txn.get_balance(use_cache=False) # NOTE: do not cache this!
        usd_balance = balance['USD']['available']
        coin_balance = balance[config.get('bot.coin')]['available']
        
        # calculate balance multiplier for calculating txn size
        balance_multiplier = math.sqrt(movement_score)
        
        # get trade minimums
        min_coin, min_usd = get_minimum_trade_size()
                
        txn_side = None # must be one of [buy, sell]
        txn_size = 0 # primary/base currency
        txn_funds = 0 # secondary/quote currency
        
        # should we buy or sell? if the market direction is positive, buy. otherwise, sell.
        # NOTE: Although this seems backwards, I did a ton of tests, and the bot performs
        #   SIGNIFICANTLY better when configured this way.
        # TODO: Figure out why that is?
        if sign(movement_score) == 1:
            # the market is going up, so start buying the coin using USD
            txn_side = 'buy'
            txn_funds = usd_balance * balance_multiplier
            
            # is the transaction too small? skip if so
            if txn_funds < min_usd:
                logger.debug('Buy transaction of %.4f USD is too small to consider.' % txn_funds)
                txn_size = 0
                txn_funds = 0
        else:
            # the market is going down, so start selling the coin for USD
            txn_side = 'sell'
            txn_size = coin_balance * balance_multiplier
            
            # is the transaction too small? skip if so
            if txn_size < min_coin:
                logger.debug('Sell transaction of %.4f coin is too small to consider.' % txn_size)
                txn_size = 0
                txn_funds = 0
        
        if not (txn_size == 0 and txn_funds == 0):
            # place order
            order = txn.order(txn_side, txn_size, txn_funds)
    else:
        logger.debug('Movement change score %.2f IS NOT large enough to justify taking action.' % movement_change_score)

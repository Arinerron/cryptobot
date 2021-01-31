#!/usr/bin/env python3

from cryptobot import config, logger, database, notifier

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


is_bull_market = lambda movement_score: sign(movement_score) == 1
is_bear_market = lambda movement_score: sign(movement_score) == -1

# returns -1 or 1 depending on whether it's a positive or negative number
def sign(value: float) -> int:
    return abs(value) / value


# rounds n to nearest m
# round_dec(1.2345, 0.001) -> 1.235
def round_dec(n: float, m: float) -> float:
    num_zeros = lambda n: math.ceil(math.log(1 / n) / math.log(10))
    return round(float(n), num_zeros(float(m)))


# normalize movement score by forcing it to be between certain values (using a curve)
def curve(value: float, max_score: int) -> float:
    return sign(value) * max_score * (1 + (-1 / math.sqrt(abs(value) + 1)))


# number of seconds => human readable format
# XXX/TODO: refactor: move this to logger.py
def format_seconds(seconds: int) -> str:
    f = {
        'y': 31557600, # roughly
        'mo': 2592000, # roughly
        'd': 60*60*24,
        'h': 60*60,
        'm': 60,
        's': 1,
    }

    build = ''
    seconds = int(seconds)
    for fmt, s in f.items():
        if seconds < s:
            continue

        build += str(seconds // s) + fmt
        seconds = seconds - ((seconds // s) * s)

    return build


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
    usd_balance = float(balance['USD']['balance'])
    coin_balance = float(balance[config.get('bot.coin')]['balance'])
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
# test_run doesn't save record of the run and bypasses stale checks. warning: will make txns
def analyze_market(test_run: bool=False) -> bool:
    movement_score = get_movement_score()
    logger.debug('Movement score: %.6f' % movement_score)
    last_movement_score = None

    # find the last_movement_score from the database
    c = database.database()
    r = c.execute('SELECT datetime(`ts`, \'localtime\'), `score` FROM `movement_score_history` WHERE `product_id`=? ORDER BY id DESC LIMIT 1', (config.get('bot.coin') + '-USD',))
    row = r.fetchone()
    c.close()

    # if there was result (i.e. this is not the first run)
    if row:
        ts, last_movement_score = row
        time_since_last_run = time.time() - datetime.datetime.strptime(ts, '%Y-%m-%d %H:%M:%S').timestamp()

        time_buffer = 60 * 5 # how many seconds off is acceptable
        analysis_runs_every = 60 * 60 # how many seconds between each run. DO NOT CHANGE THIS!

        # ensure the last movement score is valid
        if time_since_last_run < analysis_runs_every - time_buffer and not test_run:
            # nope! it's already run, so we don't need to / shouldn't run it again
            logger.warning('Skipping analysis as it ran %s ago which is within the last hour.' % format_seconds(time_since_last_run))
            logger.debug('You should rerun analysis in %s.' % (format_seconds(analysis_runs_every - time_since_last_run)))
            return False
        elif time_since_last_run > (2 * analysis_runs_every) + time_buffer and not test_run:
            # nope! the change score is too old
            # otherwise we could misinterpret the movement change score
            logger.warning('Analysis last run %s ago, rendering last movement score stale.' % format_seconds(time_since_last_run))
            return False
        else:
            logger.debug('Last analysis job was %s ago.' % format_seconds(time_since_last_run))

    # store the movement score in the db for future fetching regardless of if first run
    if not test_run:
        c = database.database()
        c.execute('INSERT INTO `movement_score_history` (`product_id`, `score`) VALUES (?, ?)', (config.get('bot.coin') + '-USD', movement_score))
        database.commit()
        c.close()

    # check if first run
    if last_movement_score == None:
        # nope! we need at least one data point for analysis
        logger.warning('Skipping analysis as this is the first run.')
        return False

    # find the change in movement scores and normlize to 0 to 1 (instead of 0 to len(WEIGHTS)*2)
    movement_change_score = abs(movement_score - last_movement_score) / (len(WEIGHTS) * 2)
    minimum_movement_change_score_to_take_action = 1 / (2 * VOLATILITY)

    assert movement_change_score >= 0, 'Movement change score of %.4f must be >= 0. Current movement score is %.4f and last movement score is %.4f.' % (movement_change_score, movement_score, last_movement_score)
    assert minimum_movement_change_score_to_take_action >= 0, 'Minimum movement change score required to take action is %.4f which is < 0.' % minimum_movement_change_score_to_take_action

    # check if we should take action
    if movement_change_score >= minimum_movement_change_score_to_take_action:
        logger.debug('Movement change score %.6f is large enough to justify taking action.' % movement_change_score)

        # get the current balance
        balance = txn.get_balance(use_cache=False) # NOTE: do not cache this!
        usd_balance = float(balance['USD']['available'])
        coin_balance = float(balance[config.get('bot.coin')]['available'])

        # calculate balance multiplier for calculating txn size
        balance_multiplier = math.sqrt(abs(movement_change_score))
        assert balance_multiplier <= 1, 'Invalid balance multiplier: > 1'
        assert balance_multiplier >= 0, 'Invalid balance multiplier: < 0'

        # get trade minimums
        min_coin, min_usd = get_minimum_trade_size()

        txn_side = None # must be one of [buy, sell]
        txn_size = 0 # primary/base currency
        txn_funds = 0 # secondary/quote currency

        # should we buy or sell? if the market direction is positive, buy. otherwise, sell.
        # NOTE: Although this seems backwards, I did a ton of tests, and the bot performs
        #   SIGNIFICANTLY better when configured this way.
        # TODO: Figure out why that is?
        if is_bull_market(movement_score):
            # the market is going up, so start buying the coin using USD
            txn_side = 'buy'
            txn_funds = usd_balance * balance_multiplier

            # is the transaction too small? skip if so
            if txn_funds < min_usd:
                logger.debug('Buy transaction of %.4f USD is too small to consider.' % txn_funds)
                txn_size = 0
                txn_funds = 0
        elif is_bear_market(movement_score):
            # the market is going down, so start selling the coin for USD
            txn_side = 'sell'
            txn_size = coin_balance * balance_multiplier

            # is the transaction too small? skip if so
            if txn_size < min_coin:
                logger.debug('Sell transaction of %.4f coin is too small to consider.' % txn_size)
                txn_size = 0
                txn_funds = 0
        else:
            raise ValueError('Movement score %.4f did not qualify as bear or bull market!' % movement_score)

        # check if we should place an order (both 0's -> no order)
        assert txn_side
        if txn_size or txn_funds:
            assert not (txn_size and txn_funds)

            txn_size = round_dec(txn_size, config.get('bot.increments.coin'))
            txn_funds = round_dec(txn_funds, config.get('bot.increments.usd'))

            # make pretty print
            logger.debug('Balance before transaction :: %.4f %s || %.2f USD' % (coin_balance, config.get('bot.coin'), usd_balance))
            message = f'Placing {config.get("bot.coin")}-USD {txn_side.upper()} order of ' + str('%.4f coin' % txn_size if txn_size else '$%.02f USD' % txn_funds) + '...'
            logger.info(message)
            notifier.send('order', message)

            # place order
            order = txn.order(txn_side, txn_size, txn_funds)
            return order
    else:
        logger.debug('Movement change score %.6f IS NOT large enough to justify taking action.' % movement_change_score)

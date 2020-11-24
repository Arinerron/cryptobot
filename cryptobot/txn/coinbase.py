#!/usr/bin/env python3

import requests
import time
import cryptobot.coinbase

CACHE_TIMEOUT = 10

class Account:
    balance = None
    _balance_cache_time = None

    @staticmethod
    def get_balance(use_cache = True):
        cur_time = time.time()

        if (not use_cache) or (not Account._balance_cache_time or Account._balance_cache_time + CACHE_TIMEOUT < cur_time):
            # cache expired, refetch
            Account.balance = cryptobot.coinbase.coinbase_accounts()
            Account._balance_cache_time = cur_time

        return Account.balance


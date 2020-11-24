#!/usr/bin/env python3

import cryptobot
import time

if __name__ == '__main__':
    import json
    #print(json.dumps(cryptobot.coinbase.coinbase_accounts()))
    account = cryptobot.txn.coinbase.Account
    #account.get_balance()
    #account.get_balance()
    #print(json.dumps(cryptobot.coinbase.get_historic_price(1506247200)))
    j = lambda x: print(json.dumps(x))
    j(cryptobot.coinbase.get_current_price())

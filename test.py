#!/usr/bin/env python3

import cryptobot
import time
import json

if __name__ == '__main__':
    j = lambda x: print(json.dumps(x))
    j(cryptobot.txn.coinbase.get_balance())
    j(cryptobot.history.coinbase.get_current_price())
    j(cryptobot.history.coinbase.get_percent_change(time.time()-100000))
    j(cryptobot.analysis.analyze_market())

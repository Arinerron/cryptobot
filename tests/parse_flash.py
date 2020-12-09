#!/usr/bin/env python3

from cryptobot import logger
from cryptobot.flash import parse_flash

import time
import re


if __name__ == '__main__':
    cases = {
        '5% in 60s': (0.05, 60),
        '5% in 1m': (0.05, 60),
        '5% in 60': (0.05, 60),
        '0.05 in 3m': (0.05, 60*3),
        '0.05 in 3min': (0.05, 60*3),
        '120% in 2h': (1.20, 60*60*2),
        '0.05 in 2h5m20s': (0.05, 60*60*2 + 60*5 + 20),
        '0.05 in 2h5.75m20s': (0.05, 60*60*2 + 60*(5.75) + 20),
        ' 55% in 65min   ': (0.55, 60*65)
    }

    logger.debug('Testing %d flash parsing cases...' % len(cases))
    for case, expected_value in cases.items():
        logger.debug('... testing parse_flash("%s") == %s' % (case, expected_value))
        actual_value = parse_flash(case)
        assert actual_value == expected_value, 'actual %s != expected %s for case "%s"' % (actual_value, expected_value, case)

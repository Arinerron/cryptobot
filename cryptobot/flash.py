#!/usr/bin/env python3

from cryptobot import config, logger, analysis, notifier

import re
import time


def parse_flash(case: str) -> tuple:
    case = case.strip().lower()
    assert ' in ' in case, 'Invalid case "%s"; missing " in "' % case
    assert len(case.split()) == 3, 'Invalid case "%s"; there should only be 3 spaces' % case

    percent, _, duration = case.split()

    # parse percent
    if percent.endswith('%'):
        percent = float(percent[:-1]) / 100
    else:
        percent = float(percent)

    # parse time change
    total = 0
    for number, unit in re.findall(r'([\d\.]+)([a-z]+)?', duration):
        unit_multiplier = {
            '': 1, 's': 1, 'sec': 1,
            'm': 60, 'min': 60,
            'h': 60*60, 'hr': 60*60,
            'd': 60*60*24, 'day': 60*60*24,
            'w': 60*60*24*7, 'wk': 60*60*24*7, 'week': 60*60*24*7,
            'mo': 60*60*24*7*4, # roughly
            'y': 60*8760, 'yr': 60*8760 # roughly
        }.get(unit)

        assert unit_multiplier, 'Unknown unit "%s"' % unit
        total += float(number) * unit_multiplier

    return abs(percent), total


def check_flash(use_cache: bool=False):
    bot_flash = config.get('bot.flash', [])

    assert isinstance(bot_flash, list)
    assert analysis.history
    assert analysis.is_bull_market(1)

    for case in bot_flash:
        percent_threshold, total_offset = parse_flash(case)
        percent = analysis.history.get_percent_change(time.time() - total_offset, use_cache=use_cache)
        if abs(percent) >= percent_threshold:
            message = 'Flash ' + ('crash' if analysis.is_bear_market(percent) else 'rally') + ' detected; percent change %.4f is above the %.4f threshold for %s.' % (percent, percent_threshold, analysis.format_seconds(total_offset))
            logger.info(message)
            notifier.send('flash', message)

#!/usr/bin/env python3

import cryptobot.config
import functools


LOG_CRITICAL, LOG_FATAL = 4, 4
LOG_ERROR, LOG_ERR = 3, 3
LOG_WARNING, LOG_WARN = 2, 2
LOG_INFO = 1
LOG_DEBUG, LOG_DBG = 0, 0

log_settings = {
    LOG_DEBUG: {
        'prefix': '  *'
    },
    LOG_INFO: {
        'prefix': '[*]'
    },
    LOG_WARNING: {
        'prefix': '[!]'
    },
    LOG_ERROR: {
        'prefix': '[-]'
    },
    LOG_FATAL: {
        'prefix': '[X]'
    }
}


def log(level, message):
    min_level = {
        '0': 0,
        '1': 1,
        '2': 2,
        '3': 3,
        '4': 4,
        'debug': 0,
        'dbg': 0,
        'info': 1,
        'warning': 2,
        'warn': 2,
        'error': 3,
        'err': 3,
        'critical': 4,
        'fatal': 4
    }.get(cryptobot.config.get('bot.log-level'))
    assert min_level != None, 'Invalid log level'
    assert level in log_settings

    if level < min_level:
        return

    settings = log_settings[level]
    
    print(settings['prefix'] + ' ' + str(message).strip())


critical = functools.partial(log, LOG_CRITICAL)
fatal = functools.partial(log, LOG_CRITICAL)
error = functools.partial(log, LOG_ERROR)
err = functools.partial(log, LOG_ERROR)
warning = functools.partial(log, LOG_WARNING)
warn = functools.partial(log, LOG_WARNING)
info = functools.partial(log, LOG_INFO)
debug = functools.partial(log, LOG_DEBUG)
dbg = functools.partial(log, LOG_DBG)


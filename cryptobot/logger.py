#!/usr/bin/env python3

import cryptobot.config
import functools
import datetime

import cryptobot


LOG_CRITICAL, LOG_FATAL = 4, 4
LOG_ERROR, LOG_ERR = 3, 3
LOG_WARNING, LOG_WARN = 2, 2
LOG_INFO = 1
LOG_DEBUG, LOG_DBG = 0, 0


# XXX/HACK: this is to fix the circular import
def get_log_settings() -> dict:
    return {
        LOG_DEBUG: {
            'prefix': 'DEBUG'
        },
        LOG_INFO: {
            'prefix': 'INFO'
        },
        LOG_WARNING: {
            'prefix': 'WARN'
        },
        LOG_ERROR: {
            'prefix': 'ERROR',
            'hook': functools.partial(cryptobot.notifier.send, 'error')
        },
        LOG_FATAL: {
            'prefix': 'FATAL',
            'hook': functools.partial(cryptobot.notifier.send, 'error')
        }
    }


def parse_log_level(level: str) -> int:
    log_settings = get_log_settings()
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
    }.get(level, 'error')

    assert min_level != None, 'Invalid log level'
    assert min_level in log_settings

    return min_level


def log(level: int, message: str, show_ts=True):
    log_settings = get_log_settings()

    file_level = parse_log_level(cryptobot.config.get('bot.log.file', 'err'))
    stdout_level = parse_log_level(cryptobot.config.get('bot.log.stdout', 'err'))

    settings = log_settings[level]
    data = settings['prefix'] + '\t' + ('[' + str(datetime.datetime.utcnow()) + ' UTC] ' if show_ts else '') + str(message).strip()

    if level >= stdout_level:
        print(data)
    if level >= file_level:
        with open('/var/log/cryptobot.log', 'a') as f:
            f.write(data + '\n')

    if settings.get('hook'):
        settings.get('hook')(message)


critical = functools.partial(log, LOG_CRITICAL)
fatal = functools.partial(log, LOG_CRITICAL)
error = functools.partial(log, LOG_ERROR)
err = functools.partial(log, LOG_ERROR)
warning = functools.partial(log, LOG_WARNING)
warn = functools.partial(log, LOG_WARNING)
info = functools.partial(log, LOG_INFO)
debug = functools.partial(log, LOG_DEBUG)
dbg = functools.partial(log, LOG_DBG)

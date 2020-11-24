#!/usr/bin/env python3

import yaml

CONFIG_PATHS = ['/usr/share/cryptobot/config.yml']
CONFIG = None

class Config(dict):
    pass

for path in CONFIG_PATHS:
    try:
        with open(path, 'r') as f:
            CONFIG = Config(yaml.safe_load(f.read()))
    except FileNotFoundError:
        continue

assert CONFIG != None, 'No config file found at %s' % CONFIG_PATHS[0] # XXX: bad code

def get(key, default=None):
    last_dict = CONFIG
    for segment in key.split('.'):
        assert isinstance(last_dict, dict)
        last_dict = last_dict.get(segment, default)
    return last_dict

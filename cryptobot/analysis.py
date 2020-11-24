#!/usr/bin/env python3

import math

max_val = 5

def sign(value):
    return abs(value) / value

# normalize
def curve(value: float, max_val: int=max_val) -> float:
    return sign(value) * max_val * (1 + (-1 / math.sqrt(abs(value) + 1)))

# calculate the price movement score
def get_score(history):
    weights = {
        1: 0.4, # 1 hour ago
        1 * 24: 0.3, # 1 day ago
        1 * 24 * 7: 0.2, # 1 week ago
        1 * 24 * 7 * 4: 0.1 # 1 month ago
    }

    raw_score = 0

    for period, weight in weights.items():
        change = history.get_change(hours = period)
        assert change != None, "Not enough price history to calculate score!"
        raw_score += weight * change

    score = curve(raw_score)
    return score

from itertools import chain, combinations

import lz4.block
import numpy as np


def keystoint(x):
    return {int(k): v for k, v in x.items()}


def decompress(bytes):
    length = sum([
        (bytes[4 + i] & 0xFF) << 8 * i
        for i in range(4)
    ])
    return lz4.block.decompress(bytes[16:], length, True)


def sortbased_randn(N, notes):
    bins = np.zeros((N, notes, 3))
    simulated_play = np.digitize(np.random.randn(N, notes), bins=[-1, 1])
    for i in range(3):
        bins[:, :, i] = simulated_play == i
    return bins


def powerset(iterable):
    s = list(iterable)
    return chain.from_iterable(combinations(s, r) for r in range(len(s) + 1))

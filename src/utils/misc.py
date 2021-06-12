import os
from itertools import chain, combinations
from math import ceil, log2

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


class SegmentTree:
    """
    It looks like this for n0,n1,n2,n3,n4,n5,n6,n7,n8,n9,n10,n11,n12
    0                                                                     0
    1:3                                  0                               n7
    3:7                  0              n3               n7             999
    7:15         0      n1      n3      n5      n7       n9     n11     999
    15:31    0  n0  n1  n2  n3  n4  n5  n6  n7  n8  n9  n10 n11 n12 999 999
    """

    def __init__(self, init_array, activations, deactivations, n_skills):
        self.array = [0] + init_array + [9E9]
        self.size = len(self.array)
        self.depth = int(ceil(log2(self.size))) + 1
        self.tree_size = 2 ** self.depth - 1
        self.timing_tree = [0] * self.tree_size
        self.skill_tree = list()
        # Cannot use [set()] * self.tree_size since all the sets have the same pointer somehow
        for _ in range(self.tree_size):
            self.skill_tree.append(set())
        self._construct_tree_subroutine(tree_idx=0, depth=0)
        self._generate_skill_tree(activations, deactivations, n_skills)

    def _construct_tree_subroutine(self, tree_idx, depth):
        # Termination case
        if depth == self.depth - 1:
            arr_idx = tree_idx + 1 - 2 ** depth
            if arr_idx >= self.size:
                self.timing_tree[tree_idx] = 9E9
            else:
                self.timing_tree[tree_idx] = self.array[arr_idx]
            return self.timing_tree[tree_idx]
        # Divide and conquer case
        self.timing_tree[tree_idx] = min(
            self._construct_tree_subroutine(tree_idx=tree_idx * 2 + 1, depth=depth + 1),
            self._construct_tree_subroutine(tree_idx=tree_idx * 2 + 2, depth=depth + 1)
        )
        return self.timing_tree[tree_idx]

    def _generate_skill_tree(self, activations, deactivations, n_skills):
        skill_activation_tracker = [False] * n_skills
        for arr_idx, arr_v in enumerate(self.array):
            # Skip the 0 and 9E9 values
            if arr_v == 0:
                continue
            if arr_v == 9E9:
                break
            tree_idx = arr_idx - 1 + 2 ** (self.depth - 1)
            if arr_v in activations:
                for activated in activations[arr_v]:
                    skill_activation_tracker[activated] = True
            if arr_v in deactivations:
                for deactivated in deactivations[arr_v]:
                    skill_activation_tracker[deactivated] = False
            for skill_idx, activated in enumerate(skill_activation_tracker):
                if activated:
                    self.skill_tree[tree_idx].add(skill_idx)
        self._fill_skill_tree_subrountine(0, 0)

    def _fill_skill_tree_subrountine(self, tree_idx, depth):
        # Termination case
        if depth == self.depth - 2:
            arr_idx = tree_idx + 1 - 2 ** depth
            return self.skill_tree[tree_idx]
        # Divide and conquer case
        self.skill_tree[tree_idx] = self._fill_skill_tree_subrountine(tree_idx=tree_idx * 2 + 1,
                                                                      depth=depth + 1).intersection(
            self._fill_skill_tree_subrountine(tree_idx=tree_idx * 2 + 2, depth=depth + 1))
        self.skill_tree[tree_idx * 2 + 1] = self.skill_tree[tree_idx * 2 + 1].difference(self.skill_tree[tree_idx])
        self.skill_tree[tree_idx * 2 + 2] = self.skill_tree[tree_idx * 2 + 2].difference(self.skill_tree[tree_idx])
        return self.skill_tree[tree_idx]

    def query(self, x):
        trace = list()
        depth = 1
        idx = 0
        while depth < self.depth:
            left = idx * 2 + 1
            right = idx * 2 + 2
            # Go left
            if x <= self.timing_tree[right]:
                idx = left
            else:
                idx = right
            trace.append(idx)
            depth += 1
        res = set()
        for _ in trace:
            res = res.union(self.skill_tree[_])
        return res

    def __str__(self):
        res = ""
        for depth in range(self.depth):
            res += "\t".join(map(str, self.skill_tree[2 ** depth - 1:2 ** (depth + 1) - 1])) + "\n"
        return res


def is_debug_mode():
    if "DEBUG_MODE" not in os.environ:
        os.environ["DEBUG_MODE"] = "0"
    return os.environ["DEBUG_MODE"] == "1"

import csv
import sys

import numpy as np

from src.logic.card import Card
from src.logic.live import Live
from src.logic.unit import Unit
from src.simulator import Simulator
from src.static.song_difficulty import Difficulty

if __name__ == '__main__':
    cards = list()
    with open("cards.txt") as fr:
        for line in fr:
            split = line.strip().split()
            cards.append(Card.from_query(split[0], custom_pots=tuple(map(int, split[1:6]))))
    unit = Unit.from_list(cards)

    live = Live()
    live.set_music(score_id=int(sys.argv[1]), difficulty=Difficulty.MPLUS)
    live.set_unit(unit)
    sim = Simulator(live)
    try:
        n_intervals = int(sys.argv[3])
    except IndexError:
        n_intervals = 40
    perfect_score, score_array = sim.simulate_theoretical_max(support=113290, n_intervals=n_intervals)

    max_score = score_array.max(axis=1)
    abuse_list = list()
    with open("abuse.csv", 'w', newline='') as fw:
        csv_writer = csv.writer(fw)
        csv_writer.writerow(["Note", "Time", "Type", "Lane", "Perfect Score", "Left", "Right", "Delta", "Window"])
        for idx in range(len(max_score)):
            temp = np.array(range(1, n_intervals + 2)) * (score_array[idx, :] == max_score[idx])
            temp = temp[temp != 0] - 1
            delta = max_score[idx] - perfect_score[idx]
            csv_writer.writerow([idx, sim.notes_data['sec'][idx], sim.notes_data['note_type'][idx],
                                 sim.notes_data['finishPos'][idx],
                                 perfect_score[idx],
                                 -200 + temp.min() * 400 / n_intervals,
                                 -200 + temp.max() * 400 / n_intervals,
                                 delta,
                                 (temp.max() - temp.min()) * 400 / n_intervals
                                 ])
            if delta > 0:
                abuse_list.append(delta)


    def is_subset_sum(set, n, sum, l):
        if sum == 0:
            return l
        if n == 0:
            return None
        if set[n - 1] > sum:
            return is_subset_sum(set, n - 1, sum, l)
        return is_subset_sum(set, n - 1, sum, l) or is_subset_sum(set, n - 1, sum - set[n - 1], l + [set[n - 1]])


    score_diff = int(sys.argv[2]) - perfect_score.sum()
    res = is_subset_sum(abuse_list, len(abuse_list), score_diff, list())
    if res is not None:
        with open("results.txt", 'w') as fw:
            fw.write(",".join(map(str, res)))
        print(res)
    else:
        print("No valid set found")
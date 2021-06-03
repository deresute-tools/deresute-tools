import csv
import time
from collections import defaultdict
from enum import Enum

import numpy as np
import pandas as pd

import customlogger as logger
from settings import ABUSE_CHARTS_PATH
from static.color import Color
from static.live_values import WEIGHT_RANGE, DIFF_MULTIPLIERS
from static.note_type import NoteType
from static.skill import get_sparkle_bonus
from static.song_difficulty import FLICK_DRAIN, NONFLICK_DRAIN
from utils.misc import SegmentTree
from utils.storage import get_writer

SPECIAL_OFFSET = 0.075


def has_skill(timestamp, upskills):
    # Faster than np.any due to early termination. Faster than iterating through elements because numpy implementation.
    for value in np.multiply(timestamp - upskills[:, 0] - 0.0001, upskills[:, 1] - timestamp):
        if value >= 0:
            return True
    return False


def check_long(notes_data, mask):
    stack = dict()
    for idx, row in notes_data.iterrows():
        if not mask[idx]:
            continue
        lane = row['finishPos']
        if row['note_type'] == NoteType.LONG and lane not in stack:
            stack[lane] = idx
        elif lane in stack:
            stack.pop(lane)
            notes_data.loc[idx, 'is_long'] = True


class Judgement(Enum):
    PERFECT = 0
    GREAT = 1
    MISS = 2


class BaseSimulationResult:
    def __init__(self):
        pass


class MaxSimulationResult(BaseSimulationResult):
    def __init__(self, total_appeal, total_perfect, abuse_df, total_life, perfect_score, cards, max_score):
        super().__init__()
        self.total_appeal = total_appeal
        self.total_perfect = total_perfect
        self.abuse_df = abuse_df
        self.total_life = total_life
        self.perfect_score = perfect_score
        self.cards = cards
        self.max_score = max_score


class SimulationResult(BaseSimulationResult):
    def __init__(self, total_appeal, perfect_score, skill_off, base, deltas, total_life, fans,
                 max_theoretical_result: MaxSimulationResult = None):
        super().__init__()
        self.total_appeal = total_appeal
        self.perfect_score = perfect_score
        self.skill_off = skill_off
        self.base = base
        self.deltas = deltas
        self.total_life = total_life
        self.fans = fans
        self.max_theoretical_result = max_theoretical_result


class AutoSimulationResult(BaseSimulationResult):
    def __init__(self, total_appeal, total_life, score, perfects, misses, max_combo, lowest_life, lowest_life_time,
                 all_100):
        super().__init__()
        self.total_appeal = total_appeal
        self.total_life = total_life
        self.score = score
        self.perfects = perfects
        self.misses = misses
        self.max_combo = max_combo
        self.lowest_life = lowest_life
        self.lowest_life_time = lowest_life_time
        self.all_100 = all_100


class Simulator:
    def __init__(self, live=None, special_offset=None, left_inclusive=False, right_inclusive=True):
        self.live = live
        self.left_inclusive = left_inclusive
        self.right_inclusive = right_inclusive
        if special_offset is None:
            self.special_offset = 0
        else:
            self.special_offset = special_offset

    def _setup_simulator(self, appeals=None, support=None, extra_bonus=None, chara_bonus_set=None, chara_bonus_value=0,
                         special_option=None, special_value=None, auto=False, mirror=False):
        self.live.set_chara_bonus(chara_bonus_set, chara_bonus_value)
        if extra_bonus is not None or special_option is not None:
            if extra_bonus is not None:
                assert isinstance(extra_bonus, np.ndarray) and extra_bonus.shape == (5, 3)
            self.live.set_extra_bonus(extra_bonus, special_option, special_value)
        self.notes_data = self.live.notes
        self.song_duration = self.notes_data.iloc[-1].sec
        self.note_count = len(self.notes_data)

        if mirror and self.live.is_grand_chart:
            start_lanes = 16 - (self.notes_data['finishPos'] + self.notes_data['status'] - 1)
            self.notes_data['finishPos'] = start_lanes

        is_flick = self.notes_data['note_type'] == NoteType.FLICK
        is_long = self.notes_data['note_type'] == NoteType.LONG
        is_slide = self.notes_data['note_type'] == NoteType.SLIDE
        is_slide = np.logical_or(is_slide, np.logical_and(self.notes_data['type'] == 3, is_flick))
        self.notes_data['is_flick'] = is_flick
        self.notes_data['is_long'] = is_long
        self.notes_data['is_slide'] = is_slide
        check_long(self.notes_data, np.logical_or(is_long, is_flick))

        weight_range = np.array(WEIGHT_RANGE)
        weight_range[:, 0] = np.trunc(WEIGHT_RANGE[:, 0] / 100 * len(self.notes_data) - 1)
        for idx, (bound_l, bound_r) in enumerate(zip(weight_range[:-1, 0], weight_range[1:, 0])):
            self.notes_data.loc[int(bound_l):int(bound_r), 'weight'] = weight_range[idx][1]
        if support is not None:
            self.support = support
        else:
            self.support = self.live.get_support()
        if appeals:
            self.total_appeal = appeals
        else:
            self.total_appeal = self.live.get_appeals() + self.support
        self.base_score = DIFF_MULTIPLIERS[self.live.level] * self.total_appeal / len(self.notes_data)

        if auto:
            self.original_notes_data = self.notes_data
            self.notes_data = pd.DataFrame(columns=self.notes_data.columns)
            secs = list(set(self.original_notes_data['sec']).union(set(np.arange(9, self.song_duration + 1, 0.05))))
            self.notes_data['sec'] = sorted(secs)
            self.notes_data['type'] = 1
            self.notes_data['startPos'] = 1
            self.notes_data['finishPos'] = 1
            self.notes_data['status'] = 0
            self.notes_data['sync'] = 0
            self.notes_data['groupId'] = 0
            self.notes_data['note_type'] = NoteType.TAP
            self.notes_data['is_flick'] = False
            self.notes_data['is_long'] = False
            self.notes_data['is_slide'] = False
            self.notes_data['weight'] = 0

    def get_note_scores(self, skill_off=False, grouped=False, auto=False):
        if not skill_off:
            bonuses_0 = (1 + self.notes_data['bonuses_0'] / 100)
            bonuses_1 = (1 + self.notes_data['bonuses_1'] / 100)
        else:
            bonuses_0 = 1
            bonuses_1 = 1
        if grouped:
            self.notes_data['note_score'] = np.round(
                self.base_score * self.notes_data['weight'] * bonuses_0 * bonuses_1)
            scores_without_miss = self.notes_data.groupby('rep')['note_score']
        else:
            scores_without_miss = np.round(self.base_score * self.notes_data['weight'] * bonuses_0 * bonuses_1)
        if auto:
            return scores_without_miss * (1 - self.notes_data['is_miss'])
        else:
            return scores_without_miss

    def simulate(self, times=100, appeals=None, extra_bonus=None, support=None, perfect_play=False,
                 chara_bonus_set=None, chara_bonus_value=0, special_option=None, special_value=None,
                 doublelife=False):
        start = time.time()
        logger.debug("Unit: {}".format(self.live.unit))
        logger.debug("Song: {} - {} - Lv {}".format(self.live.music_name, self.live.difficulty, self.live.level))
        if perfect_play:
            times = 1
            logger.debug("Only need 1 simulation for perfect play.")
        res = self._simulate(times, appeals=appeals, extra_bonus=extra_bonus, support=support,
                             perfect_play=perfect_play,
                             chara_bonus_set=chara_bonus_set, chara_bonus_value=chara_bonus_value,
                             special_option=special_option, special_value=special_value,
                             doublelife=doublelife)
        logger.debug("Total run time for {} trials: {:04.2f}s".format(times, time.time() - start))
        return res

    def _simulate(self,
                  times=1000,
                  appeals=None,
                  extra_bonus=None,
                  support=None,
                  perfect_play=False,
                  chara_bonus_set=None,
                  chara_bonus_value=0,
                  special_option=None,
                  special_value=None,
                  doublelife=False
                  ):

        self._setup_simulator(appeals=appeals, support=support, extra_bonus=extra_bonus,
                              chara_bonus_set=chara_bonus_set, chara_bonus_value=chara_bonus_value,
                              special_option=special_option, special_value=special_value)
        grand = self.live.is_grand

        self._simulate_internal(times=times, grand=grand, time_offset=0, fail_simulate=False, doublelife=doublelife)
        perfect_score = self.get_note_scores().sum()
        skill_off = self.get_note_scores(skill_off=True).sum()

        self.notes_data["note_score"] = self.get_note_scores()
        self.notes_data["total_score"] = self.get_note_scores().cumsum()

        if perfect_play:
            base = perfect_score
            deltas = np.zeros(1)
        else:
            self._simulate_internal(times=times, grand=grand, time_offset=0, fail_simulate=True, doublelife=doublelife)
            grouped_note_scores = self.get_note_scores(grouped=True)
            totals = grouped_note_scores.sum()
            base = totals.mean()
            deltas = totals - base

        total_fans = 0
        if grand:
            base_fan = base / 3 * 0.001 * 1.1
            for _ in self.live.unit_lives:
                total_fans += int(np.ceil(base_fan * (1 + _.fan / 100))) * 5
        else:
            total_fans = int(base * 0.001 * (1.1 + self.live.fan / 100)) * 5

        logger.debug("Tensor size: {}".format(self.notes_data.shape))
        logger.debug("Appeal: {}".format(int(self.total_appeal)))
        logger.debug("Support: {}".format(int(self.live.get_support())))
        logger.debug("Support team: {}".format(self.live.print_support_team()))
        logger.debug("Mean: {}".format(int(base + np.round(deltas.mean()))))
        logger.debug("Perfect: {}".format(int(perfect_score)))
        logger.debug("Skill Off: {}".format(int(skill_off)))
        logger.debug("Max: {}".format(int(base + deltas.max())))
        logger.debug("Min: {}".format(int(base + deltas.min())))
        logger.debug("Deviation: {}".format(int(np.round(np.std(deltas)))))
        return SimulationResult(
            total_appeal=self.total_appeal,
            perfect_score=perfect_score,
            skill_off=skill_off,
            base=base,
            deltas=deltas,
            total_life=self.live.get_life(),
            fans=total_fans
        )

    def simulate_theoretical_max(self, appeals=None, extra_bonus=None, support=None,
                                 chara_bonus_set=None, chara_bonus_value=0, special_option=None, special_value=None,
                                 doublelife=False):
        start = time.time()
        logger.debug("Unit: {}".format(self.live.unit))
        logger.debug("Song: {} - {} - Lv {}".format(self.live.music_name, self.live.difficulty, self.live.level))
        res = self._simulate_theoretical_max(appeals=appeals, extra_bonus=extra_bonus, support=support,
                                             chara_bonus_set=chara_bonus_set, chara_bonus_value=chara_bonus_value,
                                             special_option=special_option, special_value=special_value,
                                             doublelife=doublelife)
        logger.debug("Total run time for: {:04.2f}s".format(time.time() - start))
        return res

    def _simulate_theoretical_max(self,
                                  appeals=None,
                                  extra_bonus=None,
                                  support=None,
                                  chara_bonus_set=None,
                                  chara_bonus_value=0,
                                  special_option=None,
                                  special_value=None,
                                  doublelife=False
                                  ):
        self._setup_simulator(appeals=appeals, support=support, extra_bonus=extra_bonus,
                              chara_bonus_set=chara_bonus_set, chara_bonus_value=chara_bonus_value,
                              special_option=special_option, special_value=special_value)
        grand = self.live.is_grand
        self._helper_mark_slide_checkpoints()
        clean_notes_data = self.notes_data.copy()
        self._simulate_internal(times=1, grand=grand, time_offset=0, fail_simulate=False, doublelife=doublelife)
        perfect_scores = self.get_note_scores().copy()

        interval_endpoints = set(self.activation_points.keys()).union(set(self.deactivation_points.keys()))
        interval_endpoints = list(sorted(list(interval_endpoints)))

        skill_interval_tree = SegmentTree(interval_endpoints, self.activation_points, self.deactivation_points,
                                          len(self.live.unit.all_cards()))

        def get_ranges(note_time, note_type, is_checkpoint):
            if note_type == NoteType.TAP:
                l_g = 80000
                r_g = 80000
                l_p = 60000
                r_p = 60000
            elif note_type == NoteType.FLICK or note_type == NoteType.LONG:
                l_g = 180000
                r_g = 180000
                l_p = 150000
                r_p = 150000
            elif not is_checkpoint:
                l_g = 0
                r_g = 0
                l_p = 200000
                r_p = 200000
            else:
                l_g = 0
                r_g = 0
                l_p = 0
                r_p = 200000

            limit_l = min(note_time - l_g, note_time - l_p)
            limit_r = max(note_time + r_g, note_time + r_p)
            points = set()
            for point in interval_endpoints:
                if limit_l <= point <= limit_r:
                    points.add(point)
                # Finished checking all possible interval endpoint
                if point > limit_r:
                    break

            # Nothing to check
            if len(points) == 0:
                return list()

            has_cc = len(self.cc_set) > 0

            def get_status(abuse_time, activated_indices):
                in_cc = has_cc and len(activated_indices.intersection(self.cc_set)) > 0
                inner_l_g = l_g
                inner_l_p = l_p if not in_cc else l_p // 2
                inner_r_p = r_p if not in_cc else r_p // 2
                inner_r_g = r_g
                if -inner_l_p <= abuse_time <= inner_r_p:
                    return Judgement.PERFECT
                if note_type == NoteType.TAP or note_type == NoteType.FLICK or note_type == NoteType.LONG:
                    if -inner_l_g <= abuse_time < -inner_l_p or inner_r_p < abuse_time <= inner_r_g:
                        return Judgement.GREAT
                return Judgement.MISS

            if len(points) > 0:
                points.add(note_time - l_g)
                points.add(note_time - l_p)
                points.add(note_time + r_p)
                points.add(note_time + r_g)
                if has_cc:
                    points.add(note_time - l_p // 2)
                    points.add(note_time + r_p // 2)

            points = list(sorted(list(points)))

            valid_intervals = list()
            perfect_hit = skill_interval_tree.query(note_time)
            last_check = (None, None)
            for check_interval in zip(points[:-1], points[1:]):
                midpoint = (check_interval[0] + check_interval[1]) // 2
                check = skill_interval_tree.query(midpoint)
                if check.issubset(perfect_hit):
                    continue
                # Merge interval if possible
                inner_status = get_status(midpoint - note_time, check)
                if inner_status is Judgement.MISS:
                    last_check = (None, None)
                    continue
                inner_is_great = inner_status is Judgement.GREAT
                if last_check is not (None, None) and last_check == (check, inner_is_great):
                    last_appended = valid_intervals[-1]
                    valid_intervals[-1] = (last_appended[0], check_interval[1], inner_is_great)
                else:
                    valid_intervals.append((check_interval[0], check_interval[1], inner_is_great))
                last_check = (check, inner_is_great)
            return valid_intervals

        self.notes_data = clean_notes_data.copy()
        self.notes_data['is_abuse'] = False
        self.notes_data['is_great'] = False
        self.notes_data['abuse_range_l'] = None
        self.notes_data['abuse_range_r'] = None
        self.notes_data['abuse_helper_note_group'] = self.notes_data.index
        for idx, row in self.notes_data.iterrows():
            # Get possible ranges
            # Evaluate ranges
            sec = int(row['sec'] * 1E6)
            abuse_ranges = get_ranges(sec, row['note_type'], row['checkpoints'])
            for abuse_range_l, abuse_range_r, is_great in abuse_ranges:
                clone_row = row.copy()
                clone_row['is_abuse'] = True
                clone_row['is_great'] = is_great
                clone_row['abuse_range_l'] = int((abuse_range_l - sec) / 1000)
                clone_row['abuse_range_r'] = int((abuse_range_r - sec) / 1000)
                clone_row['sec'] = (abuse_range_l + abuse_range_r) / 2E6
                self.notes_data = self.notes_data.append(clone_row, ignore_index=True)
        self.notes_data = self.notes_data.sort_values(by='sec', kind='mergesort', ignore_index=True)
        self._simulate_internal(times=1, grand=grand, time_offset=0, fail_simulate=False, doublelife=doublelife,
                                abuse_check=True)
        bonuses_0 = (1 + self.notes_data['bonuses_0'] / 100)
        bonuses_0[self.notes_data['is_great']] = 0.7
        bonuses_1 = (1 + self.notes_data['bonuses_1'] / 100)
        self.notes_data['final_bonus'] = bonuses_0 * bonuses_1
        self.notes_data = self.notes_data \
            .sort_values(by='final_bonus', kind='mergesort', ascending=False) \
            .drop_duplicates(['abuse_helper_note_group']) \
            .sort_values(by='abuse_helper_note_group', kind='mergesort', ignore_index=True)
        # Reset weights
        max_scores = np.round(self.base_score * self.notes_data['weight'] * self.notes_data['final_bonus'])
        self.notes_data['delta'] = max_scores - perfect_scores
        self.notes_data['sec'] = self.live.notes.sec
        abuse_df = self.notes_data[self.notes_data['is_abuse']]
        max_score = int(max_scores.sum())

        cumsum_pft = perfect_scores.cumsum()
        cumsum_max = max_scores.cumsum()
        with get_writer(ABUSE_CHARTS_PATH / "{}.csv".format(self.live.score_id), 'w', newline='') as fw:
            csv_writer = csv.writer(fw)
            csv_writer.writerow(["Card Name", "Card ID", "Vo", "Da", "Vi", "Lf", "Sk"])
            for card in self.live.unit.all_cards():
                csv_writer.writerow(
                    [str(card), card.card_id, card.vo_pots, card.da_pots, card.vi_pots, card.li_pots, card.sk_pots])
            csv_writer.writerow(["Support", self.support])
            csv_writer.writerow([])
            csv_writer.writerow(["Note", "Time", "Type", "Lane", "Perfect Score", "Left", "Right", "Delta", "Window",
                                 "Cumulative Perfect Score", "Cumulative Max Score"])
            for idx, row in self.notes_data.iterrows():
                if row['is_abuse']:
                    l = row['abuse_range_l']
                    r = row['abuse_range_r']
                    window = r - l
                else:
                    l = "N/A"
                    r = "N/A"
                    window = "N/A"
                csv_writer.writerow([idx, row['sec'], row['note_type'],
                                     row['finishPos'],
                                     perfect_scores[idx],
                                     l, r,
                                     row['delta'],
                                     window,
                                     cumsum_pft[idx],
                                     cumsum_max[idx]
                                     ])

        logger.debug("Tensor size: {}".format(self.notes_data.shape))
        logger.debug("Appeal: {}".format(int(self.total_appeal)))
        logger.debug("Support: {}".format(int(self.live.get_support())))
        logger.debug("Support team: {}".format(self.live.print_support_team()))
        logger.debug("Perfect: {}".format(int(perfect_scores.sum())))
        logger.debug("Max Abuse: {}".format(max_score))
        logger.debug("Total Abuse Count: {}".format(len(abuse_df)))
        logger.debug("Average Abuse Delta: {}".format(int(abuse_df['delta'].mean())))

        return MaxSimulationResult(total_appeal=self.total_appeal, total_perfect=perfect_scores.sum(),
                                   abuse_df=abuse_df,
                                   total_life=self.live.get_life(), perfect_score=perfect_scores,
                                   cards=self.live.unit.all_cards(), max_score=max_score)

    def simulate_auto(self, appeals=None, extra_bonus=None, support=None,
                      chara_bonus_set=None, chara_bonus_value=0, special_option=None, special_value=None,
                      time_offset=0, mirror=False, doublelife=False):
        logger.debug("Unit: {}".format(self.live.unit))
        logger.debug("Song: {} - {} - Lv {}".format(self.live.music_name, self.live.difficulty, self.live.level))
        res = self._simulate_auto(appeals=appeals, extra_bonus=extra_bonus, support=support,
                                  chara_bonus_set=chara_bonus_set, chara_bonus_value=chara_bonus_value,
                                  special_option=special_option, special_value=special_value,
                                  time_offset=time_offset, mirror=mirror, doublelife=doublelife)
        return res

    def _simulate_auto(self,
                       appeals=None,
                       extra_bonus=None,
                       support=None,
                       chara_bonus_set=None,
                       chara_bonus_value=0,
                       special_option=None,
                       special_value=None,
                       time_offset=0,
                       mirror=False,
                       doublelife=False
                       ):

        if time_offset >= 200:
            self.special_offset = 0
        elif 125 >= time_offset > 100:
            self.special_offset = 0.075
        elif time_offset > 125:
            self.special_offset = 0.2 - time_offset / 1000

        # Pump dummy notes to check for intervals where notes fail
        self._setup_simulator(appeals=appeals, support=support, extra_bonus=extra_bonus,
                              chara_bonus_set=chara_bonus_set, chara_bonus_value=chara_bonus_value,
                              special_option=special_option, special_value=special_value,
                              auto=True, mirror=mirror)
        grand = self.live.is_grand
        self._simulate_auto_internal(times=1, grand=grand, time_offset=time_offset / 1000, auto_pass=0,
                                     doublelife=doublelife)

        # Then revert
        self.notes_fail = self.notes_data[['sec', 'is_miss']].set_index('sec')
        self.notes_data = self.original_notes_data
        self._helper_mark_slide_checkpoints()
        self._simulate_auto_internal(times=1, grand=grand, time_offset=time_offset / 1000, auto_pass=1,
                                     doublelife=doublelife)

        score = self.get_note_scores(auto=True).sum()
        self.notes_data["note_score"] = self.get_note_scores(auto=True)
        self.notes_data["total_score"] = self.get_note_scores(auto=True).cumsum()

        miss_mask = np.logical_and(self.notes_data['drainable'], self.notes_data['is_miss'])
        self.notes_data.loc[miss_mask, 'combo'] = 0
        perfects = int((1 - self.notes_data['is_miss']).sum())
        misses = len(self.notes_data[miss_mask])
        max_combo = int(self.notes_data['combo'].max())
        lowest_life = int(self.notes_data['life_preclip'].min())
        lowest_life_idx = int(self.notes_data['life_preclip'].idxmin())
        lowest_life_time = self.notes_data.loc[lowest_life_idx, 'sec']
        logger.debug("Tensor size: {}".format(self.notes_data.shape))
        logger.debug("Appeal: {}".format(int(self.total_appeal)))
        logger.debug("Support: {}".format(int(self.live.get_support())))
        logger.debug("Support team: {}".format(self.live.print_support_team()))
        logger.debug("Auto score: {}".format(int(score)))
        logger.debug("Lowest life: {} - Note {}/{}s".format(lowest_life, lowest_life_idx, lowest_life_time))
        logger.debug("Perfects: {}".format(perfects))
        logger.debug("Misses: {}".format(misses))
        logger.debug("Max combo: {}".format(max_combo))
        logger.debug("Total life drained: {}".format(self.notes_data['drain'].sum()))
        return AutoSimulationResult(
            total_appeal=self.total_appeal,
            total_life=self.live.get_life(),
            score=score,
            perfects=perfects,
            misses=misses,
            max_combo=max_combo,
            lowest_life=lowest_life,
            lowest_life_time=lowest_life_time,
            all_100=self.all_100)

    def _helper_mark_slide_checkpoints(self):
        self.notes_data['checkpoints'] = False
        self.notes_data.loc[self.notes_data['note_type'] == NoteType.SLIDE, 'checkpoints'] = True
        for group_id in self.notes_data[self.notes_data['note_type'] == NoteType.SLIDE].groupId.unique():
            group = self.notes_data[
                (self.notes_data['groupId'] != 0) & (self.notes_data['groupId'] == group_id)]
            self.notes_data.loc[group.iloc[-1].name, 'checkpoints'] = False
            self.notes_data.loc[group.iloc[0].name, 'checkpoints'] = False

    def _simulate_internal(self, grand, times, fail_simulate=False, time_offset=0.0, doublelife=False,
                           abuse_check=False):
        results = self._helper_initialize_skill_activations(times=times, grand=grand,
                                                            time_offset=time_offset,
                                                            fail_simulate=fail_simulate)
        self.has_sparkle, self.has_support, self.has_alternate, self.has_refrain, self.has_magic = results

        # In case of Alternate and LS, to save one redundant Alternate evaluation, only evaluate together with LS
        np_v, np_b = self._helper_initialize_skill_bonuses(grand=grand,
                                                           sparkle=False,
                                                           alternate=self.has_alternate and not self.has_sparkle,
                                                           refrain=self.has_refrain and not self.has_sparkle,
                                                           is_magic=self.has_magic,
                                                           abuse_check=abuse_check)
        self._helper_evaluate_skill_bonuses(np_v, np_b, grand=grand, doublelife=doublelife, abuse_check=abuse_check)

        if self.has_sparkle:
            np_v, np_b = self._helper_initialize_skill_bonuses(grand=grand,
                                                               np_v=np_v, np_b=np_b,
                                                               sparkle=self.has_sparkle,
                                                               alternate=self.has_alternate,
                                                               refrain=self.has_refrain,
                                                               is_magic=self.has_magic,
                                                               abuse_check=abuse_check)
            self._helper_evaluate_skill_bonuses(np_v, np_b, grand=grand, doublelife=doublelife, abuse_check=abuse_check)

    def _simulate_auto_internal(self, times, grand, time_offset=0.0, auto_pass=0, doublelife=False):
        results = self._helper_initialize_skill_activations(times=times, grand=grand,
                                                            time_offset=time_offset,
                                                            fail_simulate=False)
        self.has_sparkle, self.has_support, self.has_alternate, self.has_refrain, self.has_magic = results

        # In case of Alternate and LS, to save one redundant Alternate evaluation, only evaluate together with LS
        np_v, np_b = self._helper_initialize_skill_bonuses(grand=grand,
                                                           sparkle=False,
                                                           alternate=self.has_alternate and not self.has_sparkle,
                                                           refrain=self.has_refrain and not self.has_sparkle,
                                                           is_magic=self.has_magic)
        self._helper_evaluate_skill_bonuses(np_v, np_b, grand=grand, auto=False, doublelife=doublelife)
        self._helper_miss_notes_in_auto(time_offset)
        if auto_pass == 0:
            return
        np_v, np_b = self._helper_initialize_skill_bonuses(grand=grand,
                                                           sparkle=False,
                                                           alternate=self.has_alternate and not self.has_sparkle,
                                                           refrain=self.has_refrain and not self.has_sparkle,
                                                           is_magic=self.has_magic)
        self._helper_evaluate_skill_bonuses(np_v, np_b, grand=grand, auto=True, doublelife=doublelife)

        if self.has_sparkle:
            np_v, np_b = self._helper_initialize_skill_bonuses(grand=grand,
                                                               np_v=np_v, np_b=np_b,
                                                               sparkle=self.has_sparkle,
                                                               alternate=self.has_alternate,
                                                               refrain=self.has_refrain,
                                                               is_magic=self.has_magic)
            self._helper_miss_notes_in_auto(time_offset)
            self._helper_evaluate_skill_bonuses(np_v, np_b, grand=grand, auto=True, doublelife=doublelife)

    def _helper_miss_notes_in_auto(self, offset):
        # Register miss when support level below 4
        #   PERFECT GREAT   NICE    BAD MISS
        #   0       1       2       3   4
        if 'bonuses_3' not in self.notes_data.columns:
            is_miss = [True] * len(self.notes_data)
        else:
            is_miss = self.notes_data['bonuses_3'] < 4

        # Get all the guarded notes
        # Normal guards
        guard_idxes = {_ for _, c in enumerate(self.live.unit.all_cards()) if c.skill.skill_type == 12}
        # Magic guards
        units_with_guard = {_ // 5 for _ in guard_idxes}
        for magic in self.magic_set:
            if magic // 5 in units_with_guard:
                guard_idxes.add(magic)
        is_guarded = self.notes_data[['skill_{}'.format(_) for _ in guard_idxes]].sum(axis=1) > 0

        # Get all pairs of longs
        long_set = set()
        long_pairs = list()
        long_stack = dict()
        for idx, row in self.notes_data.iterrows():
            lane = row['finishPos']
            if lane in long_stack:
                long_start = long_stack.pop(lane)
                long_end = idx
                long_pairs.append((long_start, long_end))
                long_set.add(long_start)
                long_set.add(long_end)
                continue
            if row['note_type'] == NoteType.LONG:
                long_stack[lane] = idx

        # Get all sets of slides
        slide_group_set = set(self.notes_data[self.notes_data['note_type'] == NoteType.SLIDE].groupId.unique().tolist())
        slide_set = set(self.notes_data[self.notes_data['groupId'].isin(slide_group_set)].index)

        # Handle the trivial case first
        simple_note_mask = ~self.notes_data.index.isin(slide_set.union(long_set))
        drain_modifier = np.ones((len(self.notes_data),))
        drainable = np.ones((len(self.notes_data),))
        drainable[simple_note_mask] = True

        secs = list(self.notes_data['sec'])
        # Drain longs
        for (long_start, long_end) in long_pairs:
            # Miss long start => long end gone
            if is_miss[long_start]:
                drainable[long_end] = False
                is_miss[long_end] = True
            else:
                check_series = self.notes_fail.loc[secs[long_start]: secs[long_end]]
                if check_series.any()[0]:
                    # Hit long start but fail in the middle
                    drainable[long_end] = True
                    is_miss[long_end] = True
                    self.notes_data.loc[long_end, 'sec'] = check_series[check_series['is_miss'].values].index[0]

        # Drain slides
        for slide_group in slide_group_set:
            if not self.live.is_grand_chart:
                slide_idxes = self.notes_data[
                    (self.notes_data['groupId'] == slide_group) & (self.notes_data['type'] == 3)].index
            else:
                slide_idxes = self.notes_data[self.notes_data['groupId'] == slide_group].index

            # Find first slide miss
            # Trivial case where the very first slide fails
            bug_check = False
            first_slide_time = self.notes_data.loc[slide_idxes[0], 'sec']
            if is_miss[slide_idxes[0]]:
                first_slide_miss = slide_idxes[0]
                drain_modifier[first_slide_miss] = 2
            else:
                first_slide_miss = -1
                bug_check = self.live.is_grand_chart \
                            and self.notes_data.loc[slide_idxes[0], 'finishPos'] \
                            + self.notes_data.loc[slide_idxes[0], 'status'] > 10
                for l, r in zip(slide_idxes[:-1], slide_idxes[1:]):
                    check_series = self.notes_fail.loc[self.notes_data.loc[l, 'sec']:self.notes_data.loc[r, 'sec']]
                    wide_bug_condition = self.live.is_grand_chart \
                                         and self.notes_data.loc[r, 'finishPos'] == 3 \
                                         and self.notes_data.loc[r, 'checkpoints']
                    grand_bug_condition = self.live.is_grand_chart \
                                          and self.notes_data.loc[r, 'finishPos'] < 10 \
                                          and self.notes_data.loc[r, 'finishPos'] + self.notes_data.loc[r, 'status'] > 6 \
                                          and self.notes_data.loc[r, 'checkpoints']
                    if wide_bug_condition or grand_bug_condition:
                        # Dumb lane 3 bug
                        first_to_hit = max(self.notes_data.loc[r, 'sec'] - offset, first_slide_time)
                        original_checkpoint_time = self.notes_data.loc[r, 'sec']
                        self.notes_data.loc[r, 'sec'] = first_to_hit
                        check_series = self.notes_fail.loc[self.notes_data.loc[l, 'sec']:self.notes_data.loc[r, 'sec']]
                        if check_series.any()[0]:
                            self.notes_data.loc[r, 'sec'] = original_checkpoint_time
                            first_slide_miss = r
                            if not bug_check:
                                self.notes_data.loc[first_slide_miss, 'sec'] = \
                                    check_series[check_series['is_miss'].values].index[0]
                            break
                        else:
                            is_miss[r] = False
                        continue
                    elif check_series.any()[0]:
                        first_slide_miss = r
                        if not bug_check:
                            self.notes_data.loc[first_slide_miss, 'sec'] = \
                                check_series[check_series['is_miss'].values].index[0]
                        break

            # If there's no miss, ignore
            if first_slide_miss == -1:
                continue
            # Check for grand bug where slides start from unit C get special treatment
            if not bug_check:
                for _ in slide_idxes:
                    if _ > first_slide_miss:
                        drainable[_] = False
                    # Mark first checkpoint as miss and drainable but all checkpoints after that are not drainable,
                    # even though they are misses as well
                    if _ >= first_slide_miss:
                        is_miss[_] = True
                continue
            # Handle the stupid bug
            for _ in slide_idxes:
                if _ > first_slide_miss:
                    drainable[_] = True
                if _ >= first_slide_miss:
                    if self.notes_data.loc[_, 'finishPos'] < 10 \
                            and self.notes_data.loc[_, 'finishPos'] + self.notes_data.loc[_, 'status'] > 6 \
                            and self.notes_data.loc[_, 'checkpoints']:
                        is_miss[_] = False
                    else:
                        is_miss[_] = True

        # Calculate combo
        self.notes_data['drainable'] = drainable
        self.notes_data['drain_modifier'] = drain_modifier
        self.notes_data['is_miss'] = is_miss
        self.notes_data = self.notes_data.sort_values(by='sec', kind='mergesort', ignore_index=True)
        self._helpter_calculate_combo()

        is_drained = np.logical_and(np.logical_and(is_miss, drainable), 1 - is_guarded)
        self.notes_data['drain'] = 0
        self.notes_data.loc[is_drained & self.notes_data['is_flick'], 'drain'] = FLICK_DRAIN[self.live.difficulty]
        self.notes_data.loc[is_drained & ~self.notes_data['is_flick'], 'drain'] = NONFLICK_DRAIN[self.live.difficulty]

    def _helpter_calculate_combo(self):
        combo = list()
        current_combo = 0
        for drain, missed in zip(self.notes_data['drainable'], self.notes_data['is_miss']):
            if missed:
                # Do not reset combo in case of not drainable (missed checkpoints due to missed slide start, etc.)
                if drain:
                    current_combo = 0
                combo.append(current_combo)
            else:
                combo.append(current_combo)
                current_combo += 1
        weight_dict = dict()
        weight_range = np.array(WEIGHT_RANGE)
        weight_range[:, 0] = np.trunc(WEIGHT_RANGE[:, 0] / 100 * len(self.notes_data) - 1)
        for idx, (bound_l, bound_r) in enumerate(zip(weight_range[:-1, 0], weight_range[1:, 0])):
            for _ in range(int(bound_l), int(bound_r)):
                weight_dict[_] = weight_range[idx][1]
        self.notes_data['combo'] = combo
        self.notes_data['weight'] = self.notes_data['combo'].map(weight_dict)
        self.notes_data['combo'] += 1

    def _helper_evaluate_skill_bonuses(self, np_v, np_b, grand, mutate_df=True, auto=False, doublelife=False,
                                       abuse_check=False):
        """
        Evaluates and unifies skill bonuses.
        :param np_v: Numpy array of unnormalized (e.g. 120) skill values (no boost), shape: Notes x Values x Colors x Cards
        :param np_b: Numpy array of unnormalized (e.g. 1200) boost values, shape: Notes x Values x Colors x Cards
        :param grand: True if GRAND LIVE, else False.
        :return: Final Series of boosted and normalized (e.g. 35%) bonuses, shape: Notes x Values
        """
        np_v = np_v.copy()  # Clone to avoid mutating tensors
        np_b = np_b.copy()
        units = 3 if grand else 1
        np_vu = np.zeros((len(self.notes_data), 4, 3, units))  # Notes x Values x Color x Units
        # Normalize boosts
        v_mask = np_v[:, :2, :, :] != 0
        b_mask = np_b[:, :3, :, :] != 0
        np_v[:, :2, :, :][v_mask] = np_v[:, :2, :, :][v_mask] - 100
        np_b[:, :3, :, :][b_mask] = np_b[:, :3, :, :][b_mask] - 1000

        # Pre-calculate total/max boosts to reduce redundant computations
        if all(map(lambda _: len(_) <= 1, self.magic_lists.values())):
            np_b_sum = np_b.sum(axis=3)
        else:
            np_b_sum = np.zeros((len(self.notes_data), 4, 3))
            for unit_idx, magics in self.magic_lists.items():
                if len(magics) <= 1:
                    unit_sum = np_b[:, :, :, unit_idx * 5:(unit_idx + 1) * 5].sum(axis=3)
                else:
                    offset_magics = [_ + unit_idx * 5 for _ in magics]
                    non_magics = [_ + unit_idx * 5 for _ in range(5) if _ not in magics]
                    magic_b_sum = np_b[:, :, :, offset_magics].max(axis=3)
                    non_magic_b_sum = np_b[:, :, :, non_magics].sum(axis=3)
                    unit_sum = np.add(magic_b_sum, non_magic_b_sum)
                np_b_sum = np.add(np_b_sum, unit_sum)
        np_b_max = np_b.max(axis=3)

        # Apply boosts to values
        for unit_idx, unit in enumerate(self.live.unit.all_units):
            if unit.resonance:
                # Resonance unit will get the total boost applied on each skill
                boost_array = np_b_sum
                # And the final skill values of the unit are summed over the unit
                agg_func = np.sum
            else:
                # Non-resonance unit will get the max boost applied on each skill
                boost_array = np_b_max
                # And the final skill values of the unit are maxed over the unit
                agg_func = np.max

            # Cache first, reset combo bonus to negative using mask later
            alt_original_values = dict()
            # Only run values 0,1,2 on non support, only run value 3 on support.
            # Support builds are not the main focus so no optimization for support.
            non_support_list = list()
            # Ignore healing boost and cut tensor product size if false
            for card_idx in range(unit_idx * 5, (unit_idx + 1) * 5):
                skill = unit.get_card(card_idx % 5).skill
                if skill.is_alternate:
                    alternate_mask = np_v[:, 1, :, card_idx] < 0
                    original_value = np_v[:, 1, :, card_idx][alternate_mask]
                    alt_original_values[card_idx] = alternate_mask, original_value
                if skill.is_support or skill.is_tuning or card_idx in self.magic_set and self.has_support:
                    mask = np_v[:, 3, :, card_idx] == 0
                    np_v[:, 3, :, card_idx] += boost_array[:, 3]
                    np_v[:, 3, :, card_idx][mask] = 0
                if not skill.is_support:
                    non_support_list.append(card_idx)
            stop_idx = 3 if self.has_healing[unit_idx] else 2
            np_v[:, :stop_idx, :, non_support_list] = np.ceil(
                np_v[:, :stop_idx, :, non_support_list] * (1 + boost_array[:, :stop_idx] / 1000)[:, :, :, None])
            for card_idx, (alternate_mask, original_value) in alt_original_values.items():
                np_v[:, 1, :, card_idx][alternate_mask] = original_value

            magics = self.magic_lists[unit_idx]
            if unit.resonance and len(magics) > 1:
                offset_magics = [_ + unit_idx * 5 for _ in magics]
                stacking_df = self.notes_data[["skill_{}".format(_) for _ in offset_magics]]
                stacking_mask = stacking_df.sum(axis=1) > 1
                stacking_mask = np.array(stacking_mask).nonzero()[0]
                stacked_magic_values = np_v[:, :, :, offset_magics].max(axis=3).max(axis=2)
                stacked_magic_values = stacked_magic_values[stacking_mask]
                for _ in offset_magics[1:]:
                    np_v[stacking_mask, :, :, _] = 0
                np_v[stacking_mask, :, unit.get_card(magics[0]).color.value, offset_magics[0]] = stacked_magic_values
            np_vu[:, :, :, unit_idx] = agg_func(np_v[:, :, :, unit_idx * 5: (unit_idx + 1) * 5], axis=3)

            if self.has_alternate:
                min_tensor = np_v[:, :, :, unit_idx * 5: (unit_idx + 1) * 5].min(axis=3)
                mask = np.logical_and(np_vu[:, :, :, unit_idx] == 0, min_tensor < 0)
                np_vu[:, :, :, unit_idx][mask] = min_tensor[mask]
        # Unify effects per unit / across colors
        skill_bonuses = np.zeros((len(self.notes_data), 4, 3))  # Notes x Values x Units
        for unit_idx, unit in enumerate(self.live.unit.all_units):
            if unit.resonance:
                # Final skill values are summed over colors
                skill_bonuses[:, :, unit_idx] = np_vu[:, :, :, unit_idx].sum(axis=2)
            else:
                # Final skill values are maxed over colors
                skill_bonuses[:, :, unit_idx] = np_vu[:, :, :, unit_idx].max(axis=2)
                if self.has_alternate:
                    min_tensor = np_vu[:, :, :, unit_idx].min(axis=2)
                    mask = np.logical_and(skill_bonuses[:, :, unit_idx] == 0, min_tensor < 0)
                    skill_bonuses[:, :, unit_idx][mask] = min_tensor[mask]
        # Unify effects across units
        skill_bonuses_final = skill_bonuses.max(axis=2)
        if self.has_alternate:
            min_tensor = skill_bonuses.min(axis=2)
            mask = np.logical_and(skill_bonuses_final == 0, min_tensor < 0)
            skill_bonuses_final[mask] = min_tensor[mask]

        if auto:
            skill_bonuses_final[self.notes_data['is_miss']] = 0
            skill_bonuses_final[self.notes_data['combo'] == 1, 1] = 0

        if mutate_df:
            # Fill values into DataFrame
            value_range = 4 if self.has_support else 3
            for _ in range(value_range):
                self.notes_data["bonuses_{}".format(_)] = skill_bonuses_final[:, _]
            # Evaluate HP
            if auto:
                clipped_life = 2 * self.live.get_life()
                start_life = self.live.get_start_life(doublelife=doublelife)
                current_life = start_life
                life_array = list()
                for _, row in self.notes_data.iterrows():
                    current_life = current_life - row['drain'] * row['drain_modifier'] + row['bonuses_2']
                    if current_life > clipped_life:
                        current_life = clipped_life
                    life_array.append(current_life)
                self.notes_data['life_preclip'] = life_array
                self.notes_data['life'] = np.clip(self.notes_data['life_preclip'], a_min=0, a_max=clipped_life)
            elif any(self.has_healing):
                if not abuse_check:
                    self.notes_data['life'] = np.clip(
                        self.live.get_start_life(doublelife=doublelife)
                        +
                        self.notes_data['bonuses_2']
                        .groupby(self.notes_data.index // self.note_count)
                        .cumsum(),
                        a_min=0, a_max=2 * self.live.get_life())
                else:
                    temp_life = list()
                    clip_life = 2 * self.live.get_life()
                    current_life = self.live.get_start_life(doublelife=doublelife)
                    for real_idx, group in self.notes_data.groupby("abuse_helper_note_group"):
                        current_life += group['bonuses_2'].max()
                        if current_life > clip_life:
                            current_life = clip_life
                        temp_life.extend([current_life] * len(group))
                    self.notes_data['life'] = temp_life

            else:
                self.notes_data['life'] = self.live.get_start_life(doublelife=doublelife)
        return skill_bonuses_final

    def _helper_initialize_skill_bonuses(self, grand, np_v=None, np_b=None, sparkle=False, alternate=False,
                                         refrain=False, is_magic=False, abuse_check=False):
        """
        Initializes skill values in DataFrame.
        :param grand: True if GRAND LIVE, else False.
        :param sparkle: True if there is at least one LS in the unit. Will replace LS value with the correct values according to HP.
        :return: 2-tuple of numpy arrays containing skill values (no boost) and boost values. Both arrays are of shape Notes x Values x Colors x Cards
        """

        def handle_boost(skill, unit_idx, card_idx):
            if not skill.color_target:
                targets = [_.value for _ in [Color.CUTE, Color.COOL, Color.PASSION]]
            else:
                targets = [skill.color.value]
            for _, __ in enumerate(skill.values):
                np_b[:, _, targets, unit_idx * 5 + card_idx] = __

        def handle_act(skill, unit_idx, idx, color, magic_array=None):
            if skill.act == NoteType.SLIDE:
                mask = self.notes_data['is_slide']
                anti_mask = np.invert(mask)
            elif skill.act == NoteType.FLICK:
                mask = self.notes_data['is_flick']
                anti_mask = np.invert(mask)
            elif skill.act == NoteType.LONG:
                mask = self.notes_data['is_long']
                anti_mask = np.invert(mask)
            else:
                return
            if magic_array is not None:
                magic_array[self.notes_data[mask].index, 0, idx] = skill.v1
                magic_array[self.notes_data[anti_mask].index, 0, idx] = skill.v0
            else:
                np_v[self.notes_data[mask].index, 0, color, unit_idx * 5 + idx] = skill.v1
                np_v[self.notes_data[anti_mask].index, 0, color, unit_idx * 5 + idx] = skill.v0

        def handle_sparkle(unit_idx, card_idx, color):
            card = self.live.unit.all_units[unit_idx].get_card(card_idx)
            trimmed_life = (self.notes_data['life'] // 10).astype(int)
            np_v[:, 0, color, unit_idx * 5 + card_idx] = 0
            np_v[:, 1, color, unit_idx * 5 + card_idx] = trimmed_life.map(
                get_sparkle_bonus(rarity=card.rarity, grand=grand))

        def handle_alternate(all_alternates, all_refrains, alt_magics):
            alternate_groups = list()
            for i in range(3):
                temp = list()
                for alt in all_alternates + alt_magics:
                    if i * 5 <= alt < (i + 1) * 5:
                        temp.append(alt)
                alternate_groups.append(temp)
            for unit_idx, alternates in enumerate(alternate_groups):
                if len(alternates) == 0:
                    continue
                non_alternate = list()
                for _ in range(unit_idx * 5, unit_idx * 5 + 5):
                    if _ in alternates or _ in all_refrains:
                        continue
                    non_alternate.append(_)
                alternate_value = np.ceil(np.clip(np_v[:, 0:1, :, non_alternate] - 100, a_min=0, a_max=9000) * 1.5)
                alternate_value[alternate_value != 0] += 100
                self.notes_data['alternate_bonus_per_note'] = alternate_value.max(axis=2).max(axis=2)
                for note_type in NoteType:
                    for mask in [
                        self.notes_data.is_slide,
                        self.notes_data.is_long,
                        np.invert(np.logical_or(self.notes_data.is_slide, self.notes_data.is_long))
                    ]:
                        inner_mask = np.logical_and(self.notes_data['note_type'] == note_type, mask)
                        self.notes_data.loc[inner_mask, 'alternate_bonus_per_note'] = np.maximum.accumulate(
                            self.notes_data.loc[inner_mask, 'alternate_bonus_per_note'], axis=0)
                alternate_value = np.array(self.notes_data['alternate_bonus_per_note'])

                for skill_idx in alternates:
                    if skill_idx not in alt_magics:
                        continue
                    # Remove values for magic alts
                    skill = self.live.unit.get_card(skill_idx).skill
                    s_arr = np_v[:, 0, skill.color.value, skill_idx]
                    c_arr = np_v[:, 1, skill.color.value, skill_idx]
                    s_arr[s_arr > 0] = 1
                    c_arr[np.logical_and(s_arr > 0, c_arr == 0)] = 80

                if abuse_check:
                    note_count = len(self.notes_data)
                else:
                    note_count = len(self.live.notes)
                if "rep" not in self.notes_data:
                    rep = 1
                else:
                    rep = self.notes_data['rep'].max() + 1
                for rep_idx in range(rep):
                    local_alternate_value = alternate_value[rep_idx * note_count: (rep_idx + 1) * note_count]
                    local_notes_data = self.notes_data[rep_idx * note_count: (rep_idx + 1) * note_count]
                    local_np_v = np_v[rep_idx * note_count: (rep_idx + 1) * note_count]
                    try:
                        first_score_note = np.argwhere(local_alternate_value > 0)[0][0]
                    except IndexError:
                        # No scoring skills
                        for skill_idx in alternates:
                            skill = self.live.unit.get_card(skill_idx).skill
                            local_np_v[:, 0:2, skill.color.value, skill_idx] = 0
                        continue
                    first_score_note = local_notes_data.iloc[first_score_note].sec
                    for skill_idx in alternates:
                        skill = self.live.unit.get_card(skill_idx).skill
                        fail_alternate_notes = local_notes_data[local_notes_data.sec < first_score_note][
                            "skill_{}_l".format(skill_idx)].max()
                        if not np.isnan(fail_alternate_notes):
                            remove_index = local_notes_data[
                                local_notes_data["skill_{}_l".format(skill_idx)] <= fail_alternate_notes].index.max()
                            # Negate where skill not activated
                            local_np_v[:remove_index + 1, 0:2, skill.color.value, skill_idx] = 0
                        local_np_v[:, 0, skill.color.value, skill_idx] = local_np_v[:, 0, skill.color.value,
                                                                         skill_idx] * local_alternate_value

        def handle_refrain(all_refrains):
            refrain_groups = list()
            for i in range(3):
                temp = list()
                for ref in all_refrains:
                    if i * 5 <= ref < (i + 1) * 5:
                        temp.append(ref)
                refrain_groups.append(temp)
            for unit_idx, refrains in enumerate(refrain_groups):
                if len(refrains) == 0:
                    continue
                non_refrain = list()
                for _ in range(unit_idx * 5, unit_idx * 5 + 5):
                    if _ in refrains or _ in self.magic_set:
                        continue
                    non_refrain.append(_)
                ref_score_value = np.ceil(np.clip(np_v[:, 0:1, :, non_refrain] - 100, a_min=0, a_max=9000))
                ref_score_value[ref_score_value != 0] += 100
                ref_combo_value = np.ceil(np.clip(np_v[:, 1:2, :, non_refrain] - 100, a_min=0, a_max=9000))
                ref_combo_value[ref_combo_value != 0] += 100
                self.notes_data['ref_score_bonus_per_note'] = ref_score_value.max(axis=2).max(axis=2)
                self.notes_data['ref_combo_bonus_per_note'] = ref_combo_value.max(axis=2).max(axis=2)
                for note_type in NoteType:
                    for mask in [
                        self.notes_data.is_slide,
                        self.notes_data.is_long,
                        np.invert(np.logical_or(self.notes_data.is_slide, self.notes_data.is_long))
                    ]:
                        inner_mask = np.logical_and(self.notes_data['note_type'] == note_type, mask)
                        self.notes_data.loc[inner_mask, 'ref_score_bonus_per_note'] = np.maximum.accumulate(
                            self.notes_data.loc[inner_mask, 'ref_score_bonus_per_note'], axis=0)
                self.notes_data['ref_combo_bonus_per_note'] = np.maximum.accumulate(
                    self.notes_data['ref_combo_bonus_per_note'], axis=0)
                ref_score_value = np.array(self.notes_data['ref_score_bonus_per_note'])
                ref_combo_value = np.array(self.notes_data['ref_combo_bonus_per_note'])
                if abuse_check:
                    note_count = len(self.notes_data)
                else:
                    note_count = len(self.live.notes)
                if "rep" not in self.notes_data:
                    rep = 1
                else:
                    rep = self.notes_data['rep'].max() + 1
                for rep_idx in range(rep):
                    local_ref_score_value = ref_score_value[rep_idx * note_count: (rep_idx + 1) * note_count]
                    local_ref_combo_value = ref_combo_value[rep_idx * note_count: (rep_idx + 1) * note_count]
                    local_notes_data = self.notes_data[rep_idx * note_count: (rep_idx + 1) * note_count]
                    local_np_v = np_v[rep_idx * note_count: (rep_idx + 1) * note_count]
                    first_score_note = None
                    first_combo_note = None
                    try:
                        first_score_note = np.argwhere(local_ref_score_value > 0)[0][0]
                    except IndexError:
                        # No scoring skills
                        for skill_idx in refrains:
                            skill = self.live.unit.get_card(skill_idx).skill
                            local_np_v[:, 0:1, skill.color.value, skill_idx] = 0
                    try:
                        first_combo_note = np.argwhere(local_ref_combo_value > 0)[0][0]
                    except IndexError:
                        # No combo skills
                        for skill_idx in refrains:
                            skill = self.live.unit.get_card(skill_idx).skill
                            local_np_v[:, 1:2, skill.color.value, skill_idx] = 0
                    if first_score_note is None:
                        first_score_note = 999
                    else:
                        first_score_note = local_notes_data.iloc[first_score_note].sec
                    if first_combo_note is None:
                        first_combo_note = 999
                    else:
                        first_combo_note = local_notes_data.iloc[first_combo_note].sec
                    for skill_idx in refrains:
                        skill = self.live.unit.get_card(skill_idx).skill
                        fail_ref_score_notes = local_notes_data[local_notes_data.sec < first_score_note][
                            "skill_{}_l".format(skill_idx)].max()
                        if not np.isnan(fail_ref_score_notes):
                            remove_index = local_notes_data[
                                local_notes_data["skill_{}_l".format(skill_idx)] <= fail_ref_score_notes].index.max()
                            # Negate score bonus where skill not activated
                            local_np_v[:remove_index + 1, 0:1, skill.color.value, skill_idx] = 0
                        fail_ref_combo_notes = local_notes_data[local_notes_data.sec < first_combo_note][
                            "skill_{}_l".format(skill_idx)].max()
                        if not np.isnan(fail_ref_combo_notes):
                            remove_index = local_notes_data[
                                local_notes_data["skill_{}_l".format(skill_idx)] <= fail_ref_combo_notes].index.max()
                            # Negate combo bonus where skill not activated
                            local_np_v[:remove_index + 1, 1:2, skill.color.value, skill_idx] = 0
                        local_np_v[:, 0, skill.color.value, skill_idx] = local_np_v[:, 0, skill.color.value,
                                                                         skill_idx] * local_ref_score_value / 1000
                        local_np_v[:, 1, skill.color.value, skill_idx] = local_np_v[:, 1, skill.color.value,
                                                                         skill_idx] * local_ref_combo_value / 1000

        def handle_magic_pass_one():
            for unit_idx, unit in enumerate(self.live.unit.all_units):
                for magic in self.magic_lists[unit_idx]:
                    # Nothing for magic to copy
                    if len(self.magic_copies[unit_idx]) == 0:
                        continue
                    np_mv = np.zeros(
                        (len(self.notes_data), 4, len(self.magic_copies[unit_idx])))  # Notes x Values x Cards
                    for magic_idx, magic_copy in enumerate(self.magic_copies[unit_idx]):
                        skill = unit.get_card(magic_copy).skill
                        if skill.act:
                            # color and unit_idx not needed
                            handle_act(skill, 0, magic_idx, 0, np_mv)
                        else:
                            np_mv[:, :, magic_idx] = np_v[:, :, :, unit_idx * 5 + magic_copy].max(axis=2).max(axis=0)
                        if skill.boost:
                            np_b[:, :, :, unit_idx * 5 + magic] = np.maximum(
                                np_b[:, :, :, unit_idx * 5 + magic],
                                np_b[:, :, :, unit_idx * 5 + magic_copy].max(axis=0))
                    np_v[:, :, unit.get_card(magic).color.value, unit_idx * 5 + magic] = np_mv.max(axis=2)

        def handle_magic_pass_two():
            trimmed_life = (self.notes_data['life'] // 10).astype(int)
            for unit_idx, unit in enumerate(self.live.unit.all_units):
                for magic_idx, magic_copy in enumerate(self.ls_magic_copies[unit_idx]):
                    card = unit.get_card(magic_copy)
                    ls_value = trimmed_life.map(get_sparkle_bonus(rarity=card.rarity, grand=grand))
                    for magic in self.magic_lists[unit_idx]:
                        np_v[:, 1, unit.get_card(magic).color.value, unit_idx * 5 + magic] = np.maximum(
                            np_v[:, 1, unit.get_card(magic).color.value, unit_idx * 5 + magic], ls_value)

        def null_deactivated_skills(unit_idx, card_idx=None):
            if card_idx is not None:
                assert isinstance(card_idx, int)
                card_range = range(unit_idx * 5 + card_idx, unit_idx * 5 + card_idx + 1)
                idx_range = range(card_idx, card_idx + 1)
            else:
                card_range = range(unit_idx * 5, (unit_idx + 1) * 5)
                idx_range = range(5)
            if self.has_support:
                value_range = 4
            elif self.has_healing[unit_idx]:
                value_range = 3
            else:
                value_range = 2
            np_v[:, :value_range, :, card_range] *= np.array(
                self.notes_data[['skill_{}'.format(unit_idx * 5 + _) for _ in idx_range]])[:, None, None, :]
            np_b[:, :value_range, :, card_range] *= np.array(
                self.notes_data[['skill_{}'.format(unit_idx * 5 + _) for _ in idx_range]])[:, None, None, :]

        units = 3 if grand else 1
        first_pass = np_v is None and np_b is None
        if first_pass:
            np_v = np.zeros((len(self.notes_data), 4, 3, 5 * units))  # Notes x Values x Colors x Cards
            np_b = np.zeros((len(self.notes_data), 4, 3, 5 * units))  # Notes x Values x Colors x Cards
        alternates = list()
        refrains = list()
        for unit_idx, unit in enumerate(self.live.unit.all_units):
            if first_pass:
                unit.convert_motif(grand=grand)
            for card_idx, card in enumerate(unit.all_cards()):
                skill = card.skill
                if skill.boost and first_pass:
                    handle_boost(skill, unit_idx, card_idx)
                else:
                    if skill.act and first_pass:
                        handle_act(skill, unit_idx, card_idx, card.skill.color.value)
                        continue
                    if skill.skill_type == 25 and sparkle:
                        handle_sparkle(unit_idx, card_idx, card.skill.color.value)
                        continue
                    elif skill.skill_type == 39 and alternate:
                        alternates.append(unit_idx * 5 + card_idx)
                    elif skill.skill_type == 40 and refrain:
                        refrains.append(unit_idx * 5 + card_idx)
                    if first_pass:
                        for _, __ in enumerate(skill.values):
                            np_v[:, _, skill.color.value, unit_idx * 5 + card_idx] = __
            null_deactivated_skills(unit_idx)
        if is_magic and first_pass:
            handle_magic_pass_one()
            for unit_idx, unit in enumerate(self.live.unit.all_units):
                for magic in self.magic_lists[unit_idx]:
                    null_deactivated_skills(unit_idx, magic)
        if alternate:
            magic_to_check = list()
            if is_magic:
                for _ in self.magic_set:
                    if int(_ // 5) in self.alt_magic_copy:
                        magic_to_check.append(_)
                cached_magic_to_check = dict()
                for _ in magic_to_check:
                    cached_magic_to_check[_] = np_v[:, :, self.live.unit.get_card(_).color.value, _].copy()
            handle_alternate(alternates, refrains, magic_to_check)
        if refrain:
            handle_refrain(refrains)
        if is_magic and not first_pass:
            handle_magic_pass_two()
            for unit_idx, unit in enumerate(self.live.unit.all_units):
                for magic in self.magic_lists[unit_idx]:
                    null_deactivated_skills(unit_idx, magic)
        return np_v, np_b

    def _helper_initialize_skill_activations(self, grand, times, time_offset=0.0, fail_simulate=False,
                                             reset_notes_data=False):
        """
        Fills in the DataFrame where each skill activates. 1 means active skill, else 0
        :param grand: True if GRAND LIVE, else False.
        :param time_offset: All notes will be offset by this amount to simulate early/late hits. Default to 0.0.
        :return: Tuple of flags required for subsequent function calls
        """
        unit_offset = 3 if grand else 1
        has_sparkle = False
        has_alternate = False
        has_support = False
        has_refrain = False
        has_magic = False
        self.has_healing = list()
        self.magic_copies = defaultdict(set)
        self.ls_magic_copies = defaultdict(set)
        self.alt_magic_copy = set()
        self.magic_lists = defaultdict(list)
        self.magic_set = set()
        self.all_100 = True
        self.cc_set = set()
        self.activation_points = defaultdict(set)
        self.deactivation_points = defaultdict(set)
        units_with_cc = set()

        if reset_notes_data:
            self.notes_data = self.original_notes_data.copy()

        if fail_simulate:
            logger.debug("Simulating fail play")
            self.notes_data = self.notes_data.append([self.notes_data] * (times - 1), ignore_index=True)
            self.notes_data['rep'] = np.repeat(np.arange(times), self.note_count)

        if self.special_offset != 0:
            self.notes_data.loc[self.notes_data['note_type'] == NoteType.FLICK, 'sec'] += self.special_offset
            self.notes_data.loc[self.notes_data['note_type'] == NoteType.LONG, 'sec'] += self.special_offset
            self.notes_data.loc[self.notes_data['note_type'] == NoteType.SLIDE, 'sec'] += self.special_offset

        for unit_idx, unit in enumerate(self.live.unit.all_units):
            for card_idx, card in enumerate(unit.all_cards()):
                skill = card.skill
                if skill.skill_type == 25:
                    has_sparkle = True
                elif skill.skill_type == 39:
                    has_alternate = True
                elif skill.skill_type == 40:
                    has_refrain = True
                elif skill.skill_type == 41:
                    has_magic = True
                if skill.v3 > 0 and not skill.boost:
                    # Use for early termination
                    has_support = True

        def left_compare(note_times_to_compare, left_to_compare):
            if self.left_inclusive:
                return note_times_to_compare >= left_to_compare
            else:
                return note_times_to_compare > left_to_compare

        def right_compare(note_times_to_compare, right_to_compare):
            if self.right_inclusive:
                return note_times_to_compare <= right_to_compare
            else:
                return note_times_to_compare < right_to_compare

        def helper_fill_lr_time_alt_ref(card_idx, has_alternate, has_refrain, left, note_times, right,
                                        unit_idx, rep_rolls=None):
            if has_alternate or has_refrain:
                mask = np.logical_and(left_compare(note_times, left), right_compare(note_times, right))
                if rep_rolls is not None:
                    mask = np.logical_and(mask, self.notes_data.rep.isin(rep_rolls))
                self.notes_data.loc[mask, 'skill_{}_l'.format(unit_idx * 5 + card_idx)] = left

        for unit_idx, unit in enumerate(self.live.unit.all_units):
            has_healing = False
            for card_idx, card in enumerate(unit.all_cards()):
                skill = card.skill
                probability = self.live.get_probability(unit_idx * 5 + card_idx)

                if probability < 1:
                    self.all_100 = False

                if probability > 0 and skill.values[2] > 0:
                    has_healing = True

                if probability > 0 and skill.skill_type != 41 and skill.skill_type != 40:
                    if skill.skill_type == 25:
                        self.ls_magic_copies[unit_idx].add(card_idx)
                    elif skill.skill_type == 39:
                        self.alt_magic_copy.add(unit_idx)
                    else:
                        self.magic_copies[unit_idx].add(card_idx)
                if probability > 0 and skill.skill_type == 41:
                    self.magic_lists[unit_idx].append(card_idx)

                if probability > 0 and skill.skill_type == 15:
                    self.cc_set.add(unit_idx * 5 + card_idx)
                    units_with_cc.add(unit_idx)

                skill_times = int((self.notes_data.iloc[-1].sec - 3) // skill.interval)
                if skill_times == 0:
                    self.notes_data['skill_{}'.format(unit_idx * 5 + card_idx)] = 0
                    continue  # Skip empty skill
                skills = np.array([
                    [skill_activation * skill.interval,
                     skill_activation * skill.interval + skill.duration]
                    for skill_activation in range(skill.offset + 1, skill_times + 1, unit_offset)])

                if not fail_simulate:
                    note_times = self.notes_data.sec + time_offset
                    self.notes_data['skill_{}'.format(unit_idx * 5 + card_idx)] = 0
                    for skill_activation, skill_range in enumerate(skills):
                        left, right = skill_range
                        self.activation_points[int(left * 1E6)].add(unit_idx * 5 + card_idx)
                        self.deactivation_points[int(right * 1E6)].add(unit_idx * 5 + card_idx)
                        self.notes_data.loc[
                            left_compare(note_times, left) & right_compare(note_times, right),
                            'skill_{}'.format(unit_idx * 5 + card_idx)] = 1 if probability > 0 else 0
                        helper_fill_lr_time_alt_ref(card_idx, has_alternate, has_refrain, left, note_times, right,
                                                    unit_idx)
                else:
                    note_times = self.notes_data.sec + np.random.random(len(self.notes_data)) * 0.06 - 0.03
                    self.notes_data['skill_{}'.format(unit_idx * 5 + card_idx)] = 0
                    for skill_activation, skill_range in enumerate(skills):
                        left, right = skill_range
                        if probability < 1:
                            rep_rolls = np.random.choice(2, times, p=[1 - probability, probability])
                            rep_rolls = rep_rolls * np.arange(1, 1 + times) - 1
                            rep_rolls = rep_rolls[rep_rolls != -1]
                            self.notes_data.loc[
                                left_compare(note_times, left) & right_compare(note_times, right)
                                & (self.notes_data.rep.isin(rep_rolls)),
                                'skill_{}'.format(unit_idx * 5 + card_idx)] = 1
                            helper_fill_lr_time_alt_ref(card_idx, has_alternate, has_refrain, left, note_times,
                                                        right, unit_idx, rep_rolls=rep_rolls)
                        else:
                            # Save a bit more time
                            self.notes_data.loc[
                                left_compare(note_times, left) & right_compare(note_times, right),
                                'skill_{}'.format(unit_idx * 5 + card_idx)] = 1
                            helper_fill_lr_time_alt_ref(card_idx, has_alternate, has_refrain, left, note_times,
                                                        right, unit_idx)

            self.has_healing.append(has_healing)

        if not has_magic:
            self.magic_copies = dict()
            self.ls_magic_copies = dict()
        else:
            for unit_idx, unit in enumerate(self.live.unit.all_units):
                for magic in self.magic_lists[unit_idx]:
                    self.magic_set.add(unit_idx * 5 + magic)
                    self.notes_data['magic_{}'.format(unit_idx * 5 + magic)] = self.notes_data[
                        'skill_{}'.format(unit_idx * 5 + magic)]
                    if unit_idx in units_with_cc:
                        self.cc_set.add(unit_idx * 5 + magic)
        return has_sparkle, has_support, has_alternate, has_refrain, has_magic

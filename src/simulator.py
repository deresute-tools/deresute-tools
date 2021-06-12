import copy
import math
import time
from collections import defaultdict
from enum import Enum
from typing import List, Dict

import numpy as np

import customlogger as logger
from logic.skill import Skill
from static.color import Color
from static.live_values import WEIGHT_RANGE, DIFF_MULTIPLIERS
from static.note_type import NoteType
from static.skill import get_sparkle_bonus

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
    def __init__(self, total_appeal, perfect_score, skill_off, base, deltas, total_life, fans, full_roll_chance,
                 max_theoretical_result: MaxSimulationResult = None):
        super().__init__()
        self.total_appeal = total_appeal
        self.perfect_score = perfect_score
        self.skill_off = skill_off
        self.base = base
        self.deltas = deltas
        self.total_life = total_life
        self.fans = fans
        self.full_roll_chance = full_roll_chance
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
        self.live.get_base_motif_appeals()
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
        self.weight_range = self.notes_data['weight'].to_list()

        if support is not None:
            self.support = support
        else:
            self.support = self.live.get_support()
        if appeals:
            self.total_appeal = appeals
        else:
            self.total_appeal = self.live.get_appeals() + self.support
        self.base_score = DIFF_MULTIPLIERS[self.live.level] * self.total_appeal / len(self.notes_data)

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
            full_roll_chance=self.full_roll_probability,
            fans=total_fans
        )

    def _simulate_internal(self, grand, times, fail_simulate=False, time_offset=0.0, doublelife=False,
                           abuse_check=False):
        result = list()
        for _ in range(times):
            impl = StateMachine(
                grand=grand,
                doublelife=doublelife,
                live=self.live,
                notes_data=self.notes_data,
                left_inclusive=self.left_inclusive,
                right_inclusive=self.right_inclusive,
                base_score=self.base_score,
                weights=self.weight_range
            )
            result.append(impl.simulate_impl())


class StateMachine:
    skill_stack: Dict[int, Skill]
    # TODO: Tuple self.skills
    skills: List[Skill]

    def __init__(self, grand, doublelife, live, notes_data, left_inclusive, right_inclusive, base_score, weights):
        self.left_inclusive = left_inclusive
        self.right_inclusive = right_inclusive

        self.grand = grand
        self.doublelife = doublelife
        self.live = live
        self.notes_data = notes_data
        self.base_score = base_score

        self.unit_offset = 3 if grand else 1
        self.note_time_stack = self.notes_data.sec.map(lambda x: int(x * 1E6)).to_list()
        self.note_type_stack = self.notes_data.note_type.to_list()
        self.weights = weights

        # List of all skills object. Should not mutate.
        self.skills = list()

        # These 3 lists have the same length and should be mutated together.
        # List of all skill timestamps, contains activations and deactivations
        self.skill_times = list()
        # List of all skill indices, indicating which skill is activating/deactivating
        self.skill_indices = list()

        # Transient values of a state
        self.skill_stack = dict()  # What skills are currently active
        self.life = self.live.get_start_life(doublelife=self.doublelife)
        self.combo = 0
        self.score = 0

        self.best_bonus_tap = 0
        self.best_bonus_long = 0
        self.best_bonus_flick = 0
        self.best_bonus_slide = 0
        self.best_alted_bonus_tap = 0
        self.best_alted_bonus_long = 0
        self.best_alted_bonus_flick = 0
        self.best_alted_bonus_slide = 0
        self.best_combo_bonus = 0

        self.last_activated_skill = None
        self.last_activated_time = -1

        self.probabilities = [
            self.live.get_probability(_)
            for _ in range(len(self.live.unit.all_cards()))
        ]
        # Dict of what cards a magic can copy from in a unit: unit_idx -> set of card_idx (including 5 * unit_idx)
        self.magic_dict = defaultdict(lambda: set())
        # In all operations, evaluate alt then ref last
        for unit_idx, unit in enumerate(self.live.unit.all_units):
            _cache_alts = list()
            for card_idx, card in enumerate(unit.all_cards()):
                skill = card.skill
                if skill.is_magic or skill.is_encore or skill.is_refrain:
                    continue
                skill_idx_with_unit_idx = unit_idx * 5 + card_idx
                if self.probabilities[skill_idx_with_unit_idx] == 0:
                    continue
                if skill.is_alternate:
                    _cache_alts.append(skill_idx_with_unit_idx)
                else:
                    self.magic_dict[unit_idx].add(skill_idx_with_unit_idx)
            for _ in _cache_alts:
                self.magic_dict[unit_idx].add(_)

        self._sparkle_bonus_ssr = get_sparkle_bonus(8, self.grand)
        self._sparkle_bonus_sr = get_sparkle_bonus(6, self.grand)

    def initialize_activation_arrays(self):
        skill_times = list()
        skill_indices = list()
        for unit_idx, unit in enumerate(self.live.unit.all_units):
            iterating_order = list()
            _cache_alts = list()
            _cache_magic = list()
            for card_idx, card in enumerate(unit.all_cards()):
                if card.skill.is_magic:
                    _cache_magic.append(card_idx)
                    continue
                if card.skill.is_alternate:
                    _cache_alts.append(card_idx)
                    continue
                iterating_order.append(card_idx)
            iterating_order = _cache_magic + iterating_order + _cache_alts
            for card_idx, card in enumerate(iterating_order):
                skill = card.skill
                self.skills.append(skill)
                idx = unit_idx * 5 + card_idx
                if self.probabilities[idx] == 0:
                    continue
                times = int((self.notes_data.iloc[-1].sec - 3) // skill.interval)
                for act_idx in range(skill.offset + 1, times + 1, self.unit_offset):
                    act = act_idx * skill.interval
                    deact = act_idx * skill.interval + skill.duration
                    skill_times.append(int(act * 1E6))
                    skill_times.append(int(deact * 1E6))
                    skill_indices.append(unit_idx * 5 + card_idx)
                    skill_indices.append(-unit_idx * 5 - card_idx)
        zipped = zip(skill_times, skill_indices)
        for (a, b, c) in sorted(zipped):
            self.skill_times.append(a)
            self.skill_indices.append(b)

    def simulate_impl(self):
        self.initialize_activation_arrays()
        while True:
            # Terminal condition
            if len(self.skill_times) == 0 and len(self.note_time_stack) == 0:
                break

            if self.note_time_stack[0] < self.skill_times[0]:
                self.handle_note()
            elif self.skill_times[0] > self.note_time_stack[0]:
                self.handle_skill()
            else:
                if (self.skill_indices[0] > 0 and self.left_inclusive) or \
                        (self.skill_indices[0] < 0 and self.right_inclusive):
                    self.handle_skill()
                    self.handle_note()
                else:
                    self.handle_note()
                    self.handle_skill()

    def handle_skill(self):
        if self.skill_indices[0]:
            self._handle_skill_activation(magic=True, magic_skill=None)
        else:
            self._handle_skill_deactivation()

    def handle_note(self):
        note_time = self.note_time_stack.pop(0)
        note_type = self.note_type_stack.pop(0)
        weight = self.weights.pop(0)
        score_bonus, combo_bonus, life_bonus, support_bonus = self.evaluate_bonuses(note_type)
        note_score = round(self.base_score * weight * (1 + combo_bonus / 100) * (1 + score_bonus / 100))
        self.life += life_bonus
        self.score += note_score

    def evaluate_bonuses(self, note_type):
        cu_v = list()
        co_v = list()
        pa_v = list()
        cu_b = list()
        co_b = list()
        pa_b = list()

        # ARRAYS[is_boost][color]
        ARRAYS = {
            False: {
                Color.CUTE: cu_v,
                Color.COOL: co_v,
                Color.PASSION: pa_v,
            },
            True: {
                Color.CUTE: cu_b,
                Color.COOL: co_b,
                Color.PASSION: pa_b,
            }
        }
        skill_value_dict = dict()

        skill: Skill
        # Pass 1: Non Alt/Ref/Magic/Encore-Alt/Encore-Ref/Encore-Magic
        for skill_idx, skill in self.skill_stack.items():
            if skill.is_magic or skill.is_alternate or skill.is_refrain:
                continue
            ARRAYS[skill.boost][skill.color].append(skill.values)
            skill_value_dict[skill_idx] = skill.values
        # Pass 2: All non Alt/Ref skill
        for skill_idx, skill in self.skill_stack.items():
            unit_idx = skill_idx // 5
            if skill.is_motif:
                bonus_0_dict[skill_idx] = self._handle_motif(unit_idx=unit_idx, skill=skill)
                continue
            if skill.act:
                bonus_0_dict[skill_idx] = self._handle_act(skill, note_type)
                continue
            if skill.is_sparkle:
                rarity = self.live.unit.all_units[unit_idx].get_card(skill_idx % 5)
                bonus_1_dict[skill_idx] = self._handle_sparkle(rarity)
                continue
        # Pass 3: Alt
        for skill_idx, skill in self.skill_stack.items():
            unit_idx = skill_idx // 5
            if skill.is_alternate:
                self._handle_alternate()
                continue
        # Pass 4: Ref
        for skill_idx, skill in self.skill_stack.items():
            unit_idx = skill_idx // 5
            if skill.is_refrain:
                self._handle_refrain()
        return 0, 0, 0, 0

    def _handle_motif(self, unit_idx, skill):
        return self.live.unit.all_units[unit_idx].convert_motif(skill.skill_type, self.grand)

    def _handle_act(self, skill, note_type):
        return skill.v1 if skill.act == note_type else skill.v0

    def _handle_sparkle(self, rarity):
        trimmed_life = self.life // 10
        if rarity > 6:
            return self._sparkle_bonus_ssr[trimmed_life]
        else:
            return self._sparkle_bonus_sr[trimmed_life]

    def _handle_magic(self, unit_idx, skill):

        for copy_idx in self.magic_dict[unit_idx]:
            magic_skill = self.skills[copy_idx]
            self._handle_skill_activation(magic=True, magic_skill=magic_skill)

    def _handle_skill_activation(self, magic=False, magic_skill=None):
        def update_last_activated_skill(replace):
            """
            Update last activated skill for encore
            :type replace: True if new skill activates after the cached skill, False if same time
            """
            if self.skills[self.skill_indices[0]].is_encore:
                return
            if replace:
                self.last_activated_skill = self.skill_indices[0]
            else:
                self.last_activated_skill = min(self.last_activated_skill, self.skill_indices[0])

        def update_highest_score_bonus(uhb_skill):
            if uhb_skill.is_alternate:
                # Once alt is called, we can be sure it's the last skill either in magic or in a unit in case of shared timer between multiple skills
                self.best_alted_bonus_tap = max(self.best_alted_bonus_tap,
                                                math.ceil(uhb_skill.values[0] * self.best_bonus_tap))
                self.best_alted_bonus_long = max(self.best_alted_bonus_long,
                                                 math.ceil(uhb_skill.values[0] * self.best_bonus_long))
                self.best_alted_bonus_flick = max(self.best_alted_bonus_flick,
                                                  math.ceil(uhb_skill.values[0] * self.best_bonus_flick))
                self.best_alted_bonus_slide = max(self.best_alted_bonus_slide,
                                                  math.ceil(uhb_skill.values[0] * self.best_bonus_slide))
                return
            if uhb_skill.is_motif:
                motif_value = self._handle_motif(self.skill_indices[0] // 5, uhb_skill)
                self.best_bonus_tap = max(self.best_bonus_tap, motif_value)
                self.best_bonus_long = max(self.best_bonus_long, motif_value)
                self.best_bonus_flick = max(self.best_bonus_flick, motif_value)
                self.best_bonus_slide = max(self.best_bonus_slide, motif_value)
            elif uhb_skill.is_magic:
                magic_value, magic_boost = self._handle_magic(self.skill_indices[0] // 5, uhb_skill)
            else:
                self.best_bonus_tap = max(self.best_bonus_tap, uhb_skill.values[0])
                self.best_bonus_long = max(self.best_bonus_long, uhb_skill.values[0])
                self.best_bonus_flick = max(self.best_bonus_flick, uhb_skill.values[0])
                self.best_bonus_slide = max(self.best_bonus_slide, uhb_skill.values[0])
                if uhb_skill.act == NoteType.LONG:
                    self.best_bonus_long = max(self.best_bonus_long, uhb_skill.values[1])
                elif uhb_skill.act == NoteType.FLICK:
                    self.best_bonus_flick = max(self.best_bonus_flick, uhb_skill.values[1])
                elif uhb_skill.act == NoteType.SLIDE:
                    self.best_bonus_slide = max(self.best_bonus_slide, uhb_skill.values[1])
            self.best_alted_bonus_tap = max(self.best_alted_bonus_tap, self.best_bonus_tap)
            self.best_alted_bonus_long = max(self.best_alted_bonus_long, self.best_bonus_long)
            self.best_alted_bonus_flick = max(self.best_alted_bonus_flick, self.best_bonus_flick)
            self.best_alted_bonus_slide = max(self.best_alted_bonus_slide, self.best_bonus_slide)

        def update_highest_combo_bonus(uhb_skill):
            if uhb_skill.act:
                return
            if uhb_skill.is_sparkle:
                rarity = self.live.unit.all_units[self.skill_indices[0] // 5].get_card(self.skill_indices[0] % 5).rarity
                self.best_combo_bonus = max(self.best_combo_bonus, self._handle_sparkle(rarity))
                return
            self.best_combo_bonus = max(self.best_combo_bonus, uhb_skill.values[1])

        can_activate = True
        if magic and magic_skill is not None:
            skill = magic_skill
        else:
            skill = self.skills[self.skill_indices[0]]

        # Let encore copy a skill if applicable
        if skill.is_encore:
            # No valid skill found, return False
            if self.last_activated_skill is None:
                can_activate = False
            else:
                # Replace encore with the skill it copies, but use encore timer
                encore_copy: Skill = copy.copy(self.skills[self.last_activated_skill])
                encore_copy.interval = skill.interval
                encore_copy.duration = skill.duration
                self.skill_stack[self.skill_indices[0]] = encore_copy
            skill = self.skill_stack[self.skill_indices[0]]
        else:
            self.skill_stack[self.skill_indices[0]] = self.skills[self.skill_indices[0]]

        # Pop deactivation out if skill cannot activate
        can_activate = can_activate and self._can_activate()
        if not can_activate:
            if not magic:
                skill_id = self.skill_stack.pop(self.skill_indices[0])
                # First index of -skill_id should be the correct value because a skill cannot activate twice before deactivating once
                pop_skill_index = self.skill_indices.index(-skill_id)
                for list_to_pop in [self.skill_times, self.skill_indices]:
                    # Pop the deactivation first to avoid messing up the index
                    list_to_pop.pop(pop_skill_index)
                    # Then pop the activation
                    list_to_pop.pop(0)
            return

        # Update last activated skill for encore
        # If new skill is strictly after cached last skill, just replace it
        if not magic:
            if self.last_activated_time < self.skill_times[0]:
                self.last_activated_time = self.skill_times[0]
                update_last_activated_skill(replace=True)
            elif self.last_activated_time == self.skill_times[0]:
                # Else update taking skill index order into consideration
                update_last_activated_skill(replace=False)

        # No need to update for ref and boost
        if not (skill.is_refrain or skill.boost):
            update_highest_score_bonus(skill)
            update_highest_combo_bonus(skill)

    def _handle_skill_deactivation(self):
        self.skill_stack.pop(-self.skill_indices[0])

    def _handle_ol_drain(self, life_requirement):
        if self.life <= life_requirement:
            self.life -= life_requirement
            return True
        else:
            return False

    def _can_activate(self, skill_idx=None, skill=None):
        """
        Checks if a skill can activate or not.
        Leave skill_idx and skill as None to use the current queued skill in the skill stack.
        Provide skill_idx and skill object to check activation condition for that skill, useful for evaluating skills
        copied by Magic.
        """
        if skill_idx is None and skill is None:
            skill_idx = self.skill_indices[0]
            skill = self.skill_stack[skill_idx]
        # Handle OL
        if skill.is_overload:
            return self._handle_ol_drain(skill.life_requirement)
        # Handle magic
        if skill.is_magic:
            unit_idx = skill_idx // 5
            if len(self.magic_dict[unit_idx]) == 0:
                return False
            for magic_copied_skill_idx in self.magic_dict[unit_idx]:
                if not self._can_activate(magic_copied_skill_idx, self.skills[magic_copied_skill_idx]):
                    return False
        return True

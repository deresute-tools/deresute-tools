import copy
import time
from enum import Enum
from typing import List, Dict, Union

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
        [unit.get_base_motif_appeals() for unit in self.live.unit.all_units]
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
        self.helen_base_score = DIFF_MULTIPLIERS[self.live.level] * self.total_appeal / len(self.notes_data)

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
                helen_base_score=self.helen_base_score,
                weights=self.weight_range
            )
            result.append(impl.simulate_impl())


class UnitCacheBonus:
    def __init__(self):
        self.tap = 0
        self.flick = 0
        self.long = 0
        self.slide = 0
        self.combo = 0

    def update(self, skill: Skill):
        # Do not update on alternate, mutual, refrain, boosters
        if skill.is_alternate or skill.is_mutual or skill.is_refrain or skill.boost:
            return
        if skill.act is not None:
            self.tap = max(self.tap, skill.v0)
            if skill.act is NoteType.LONG:
                self.long = max(self.long, skill.v1)
                self.flick = max(self.flick, skill.v0)
                self.slide = max(self.slide, skill.v0)
            elif skill.act is NoteType.FLICK:
                self.long = max(self.long, skill.v0)
                self.flick = max(self.flick, skill.v1)
                self.slide = max(self.slide, skill.v0)
            elif skill.act is NoteType.SLIDE:
                self.long = max(self.long, skill.v0)
                self.flick = max(self.flick, skill.v0)
                self.slide = max(self.slide, skill.v1)
            return
        if skill.v0 is not None and skill.v0 > 100:
            self.tap = max(self.tap, skill.v0)
            self.flick = max(self.flick, skill.v0)
            self.long = max(self.long, skill.v0)
            self.slide = max(self.slide, skill.v0)
        if skill.v1 is not None and skill.v1 > 100:
            self.combo = max(self.combo, skill.v1)


class StateMachine:
    skill_queue: Dict[int, Union[Skill, List[Skill]]]
    # TODO: Tuple self.skills
    reference_skills: List[Skill]

    def __init__(self, grand, doublelife, live, notes_data, left_inclusive, right_inclusive, base_score,
                 helen_base_score, weights):
        self.left_inclusive = left_inclusive
        self.right_inclusive = right_inclusive

        self.grand = grand
        self.doublelife = doublelife
        self.live = live
        self.notes_data = notes_data
        self.base_score = base_score
        self.helen_base_score = helen_base_score

        self.unit_offset = 3 if grand else 1
        self.note_time_stack = self.notes_data.sec.map(lambda x: int(x * 1E6)).to_list()
        self.note_type_stack = self.notes_data.note_type.to_list()
        self.weights = weights

        # List of all skill objects. Should not mutate. Original sets.
        self.reference_skills = [None]

        # These 2 lists have the same length and should be mutated together.
        # List of all skill timestamps, contains activations and deactivations.
        self.skill_times = list()
        # List of all skill indices, indicating which skill is activating/deactivating.
        # Positive = activation, negative = deactivation.
        # E.g. 4 means the skill in slot 4 (counting from 1) activation, -4 means its deactivation
        self.skill_indices = list()

        # Transient values of a state
        self.skill_queue = dict()  # What skills are currently active
        self.life = self.live.get_start_life(doublelife=self.doublelife)
        self.combo = 0
        self.score = 0

        self.last_activated_skill = None
        self.last_activated_time = -1

        self.probabilities = [
            self.live.get_probability(_)
            for _ in range(len(self.live.unit.all_cards()))
        ]

        self._sparkle_bonus_ssr = get_sparkle_bonus(8, self.grand)
        self._sparkle_bonus_sr = get_sparkle_bonus(6, self.grand)

        self.unit_caches = list()
        for _ in range(len(self.live.unit.all_units)):
            self.unit_caches.append(UnitCacheBonus())

    def initialize_activation_arrays(self):
        skill_times = list()
        skill_indices = list()
        for unit_idx, unit in enumerate(self.live.unit.all_units):
            for card_idx, card in enumerate(unit.all_cards()):
                skill = card.skill
                self.reference_skills.append(skill)
                idx = unit_idx * 5 + card_idx
                if self.probabilities[idx] == 0:
                    continue
                times = int((self.notes_data.iloc[-1].sec - 3) // skill.interval)
                for act_idx in range(skill.offset + 1, times + 1, self.unit_offset):
                    act = act_idx * skill.interval
                    deact = act_idx * skill.interval + skill.duration
                    skill_times.append(int(act * 1E6))
                    skill_times.append(int(deact * 1E6))
                    skill_indices.append(unit_idx * 5 + card_idx + 1)
                    skill_indices.append(-unit_idx * 5 - card_idx - 1)
        zipped = zip(skill_times, skill_indices)
        for (a, b) in sorted(zipped):
            self.skill_times.append(a)
            self.skill_indices.append(b)

    def simulate_impl(self):
        self.initialize_activation_arrays()
        while True:
            # Terminal condition: No more skills and no more notes
            if len(self.skill_times) == 0 and len(self.note_time_stack) == 0:
                break

            if len(self.skill_times) == 0 or self.note_time_stack[0] < self.skill_times[0]:
                self.handle_note()
            elif len(self.note_time_stack) == 0 or self.skill_times[0] < self.note_time_stack[0]:
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
        if self.skill_indices[0] > 0:
            self._expand_encore()
            self._expand_magic()
            self._handle_skill_activation()
            # By this point, all skills that can be activated should be in self.skill_queue
            self._evaluate_motif()
            self._cache_skill_data()
            self.skill_indices.pop(0)
            self.skill_times.pop(0)
        else:
            self.skill_queue.pop(-self.skill_indices[0])
            self.skill_indices.pop(0)
            self.skill_times.pop(0)

    def handle_note(self):
        note_time = self.note_time_stack.pop(0)
        note_type = self.note_type_stack.pop(0)
        weight = self.weights[self.combo]
        self.combo += 1
        # score_bonus, combo_bonus, life_bonus, support_bonus = self.evaluate_bonuses(note_type)
        # note_score = round(self.base_score * weight * (1 + combo_bonus / 100) * (1 + score_bonus / 100))
        # self.life += life_bonus
        # self.score += note_score

    def _expand_magic(self):
        skill = self.reference_skills[self.skill_indices[0]]
        if skill.is_magic or \
                (skill.is_encore and self.skill_queue[self.skill_indices[0]].is_magic):
            unit_idx = (self.skill_indices[0] - 1) // 5
            self.skill_queue[self.skill_indices[0]] = list()
            for idx in range(unit_idx * 5, unit_idx * 5 + 5):
                copied_skill = copy.copy(self.reference_skills[idx])
                # Skip skills that cannot activate
                if self.reference_skills[idx].probability == 0:
                    continue
                # Magic does not copy itself
                if self.reference_skills[idx].is_magic:
                    continue
                # Expand encore
                if self.reference_skills[idx].is_encore:
                    # But there's nothing for encore to copy yet, skip
                    if self.last_activated_skill is None:
                        continue
                    # Or the skill for encore to copy is magic as well, skip
                    if self.reference_skills[self.last_activated_skill].is_magic:
                        continue
                    # Else let magic copy the encored skill instead
                    copied_skill = self.reference_skills[self.last_activated_skill]
                self.skill_queue[self.skill_indices[0]].append(copied_skill)

    def _expand_encore(self):
        skill = self.reference_skills[self.skill_indices[0]]
        if self.last_activated_skill is None:
            return
        if skill.is_encore:
            encore_copy: Skill = copy.deepcopy(self.reference_skills[self.last_activated_skill])
            encore_copy.interval = skill.interval
            encore_copy.duration = skill.duration
            self.skill_queue[self.skill_indices[0]] = encore_copy

    def _evaluate_motif(self):
        if self.skill_indices[0] not in self.skill_queue:
            return
        skills_to_check = self.skill_queue[self.skill_indices[0]]
        if isinstance(skills_to_check, Skill):
            skills_to_check = [skills_to_check]
        unit_idx = (self.skill_indices[0] - 1) // 5
        for skill in skills_to_check:
            if skill.is_motif:
                skill.v0 = self.live.unit.all_units[unit_idx].convert_motif(skill.skill_type)

    def _cache_skill_data(self):
        if self.skill_indices[0] not in self.skill_queue:
            return
        skills_to_check = self.skill_queue[self.skill_indices[0]]
        if isinstance(skills_to_check, Skill):
            skills_to_check = [skills_to_check]
        unit_idx = (self.skill_indices[0] - 1) // 5
        for skill in skills_to_check:
            self.unit_caches[unit_idx].update(skill)

    def _handle_skill_activation(self):
        def update_last_activated_skill(replace):
            """
            Update last activated skill for encore
            :type replace: True if new skill activates after the cached skill, False if same time
            """
            if self.reference_skills[self.skill_indices[0]].is_encore:
                return
            if replace:
                self.last_activated_skill = self.skill_indices[0]
            else:
                self.last_activated_skill = min(self.last_activated_skill, self.skill_indices[0])

        # If skill is still not queued after self._expand_magic and self._expand_encore
        if self.skill_indices[0] not in self.skill_queue:
            self.skill_queue[self.skill_indices[0]] = self.reference_skills[self.skill_indices[0]]

        # Pop deactivation out if skill cannot activate
        if not self._can_activate():
            skill_id = self.skill_queue.pop(self.skill_indices[0])
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
        if self.last_activated_time < self.skill_times[0]:
            self.last_activated_time = self.skill_times[0]
            update_last_activated_skill(replace=True)
        elif self.last_activated_time == self.skill_times[0]:
            # Else update taking skill index order into consideration
            update_last_activated_skill(replace=False)

    def _handle_ol_drain(self, life_requirement):
        if self.life <= life_requirement:
            self.life -= life_requirement
            return True
        else:
            return False

    def _check_focus_activation(self, unit_idx, skill):
        card_colors = [
            card.color
            for card in self.live.unit.all_units[unit_idx].all_cards()
        ]
        if skill.skill_type == 21:
            return not any(filter(lambda x: x is not Color.CUTE, card_colors))
        if skill.skill_type == 22:
            return not any(filter(lambda x: x is not Color.COOL, card_colors))
        if skill.skill_type == 23:
            return not any(filter(lambda x: x is not Color.PASSION, card_colors))
        # Should not reach here
        raise ValueError("Reached invalid state of focus activation check: ", skill)

    def _can_activate(self):
        """
        Checks if a (list of) queued skill(s) can activate or not.
        """
        skills_to_check = self.skill_queue[self.skill_indices[0]]
        if isinstance(skills_to_check, Skill):
            skills_to_check = [skills_to_check]
        has_failed = False
        to_be_removed = list()
        for skill in skills_to_check:
            # Handle OL
            if has_failed and skill.is_overload:
                to_be_removed.append(skill)
                continue
            if not has_failed and skill.is_overload:
                has_failed = self._handle_ol_drain(skill.life_requirement)
                if has_failed:
                    to_be_removed.append(skill)
            if skill.is_focus:
                if not self._check_focus_activation(unit_idx=self.skill_indices[0] // 5, skill=skill):
                    to_be_removed.append(skill)
        for skill in to_be_removed:
            skills_to_check.remove(skill)
        self.skill_queue[self.skill_indices[0]] = skills_to_check
        return len(skills_to_check) > 0

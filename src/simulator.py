import copy
import time
from enum import Enum
from math import ceil
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
    def __init__(self, total_appeal, perfect_score, base, deltas, total_life, fans, full_roll_chance,
                 max_theoretical_result: MaxSimulationResult = None):
        super().__init__()
        self.total_appeal = total_appeal
        self.perfect_score = perfect_score
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

        perfect_result, results, full_roll_chance = self._simulate_internal(times=times, grand=grand, time_offset=0,
                                                                            fail_simulate=False,
                                                                            doublelife=doublelife)
        perfect_score = perfect_result[0]

        if perfect_play:
            base = perfect_score
            deltas = np.zeros(1)
        else:
            score_array = np.array([result[0] for result in results])
            base = score_array.mean()
            deltas = score_array - base

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
        logger.debug("Max: {}".format(int(base + deltas.max())))
        logger.debug("Min: {}".format(int(base + deltas.min())))
        logger.debug("Deviation: {}".format(int(np.round(np.std(deltas)))))
        return SimulationResult(
            total_appeal=self.total_appeal,
            perfect_score=perfect_score,
            base=base,
            deltas=deltas,
            total_life=self.live.get_life(),
            full_roll_chance=full_roll_chance,
            fans=total_fans
        )

    def _simulate_internal(self, grand, times, fail_simulate=False, time_offset=0.0, doublelife=False,
                           abuse_check=False):
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
        impl.reset_machine(perfect=True)
        perfect = impl.simulate_impl()
        logger.debug("Scores: " + str(impl.note_scores))
        full_roll_chance = impl.full_roll_chance

        result = list()
        for _ in range(times):
            impl.reset_machine(perfect=False)
            result.append(impl.simulate_impl())
        return perfect, result, full_roll_chance


class UnitCacheBonus:
    def __init__(self):
        self.tap = 0
        self.flick = 0
        self.long = 0
        self.slide = 0
        self.combo = 0
        self.ref_tap = 0
        self.ref_flick = 0
        self.ref_long = 0
        self.ref_slide = 0
        self.ref_combo = 0
        self.alt_tap = 0
        self.alt_flick = 0
        self.alt_long = 0
        self.alt_slide = 0
        self.alt_combo = 0

    def update(self, skill: Skill):
        # Do not update on alternate, mutual, refrain, boosters
        if skill.is_alternate or skill.is_mutual or skill.is_refrain or skill.boost:
            return
        if skill.act is not None:
            self.tap = max(self.tap, skill.values[0])
            if skill.act is NoteType.LONG:
                self.long = max(self.long, skill.values[1])
                self.flick = max(self.flick, skill.values[0])
                self.slide = max(self.slide, skill.values[0])
            elif skill.act is NoteType.FLICK:
                self.long = max(self.long, skill.values[0])
                self.flick = max(self.flick, skill.values[1])
                self.slide = max(self.slide, skill.values[0])
            elif skill.act is NoteType.SLIDE:
                self.long = max(self.long, skill.values[0])
                self.flick = max(self.flick, skill.values[0])
                self.slide = max(self.slide, skill.values[1])
            return
        if skill.v0 is not None and skill.v0 > 100:
            self.tap = max(self.tap, skill.v0)
            self.flick = max(self.flick, skill.v0)
            self.long = max(self.long, skill.v0)
            self.slide = max(self.slide, skill.v0)
        if skill.v1 is not None and skill.v1 > 100:
            self.combo = max(self.combo, skill.v1)

    def update_AMR(self, skill: Skill):
        # Do not update on skills that are not alternate, mutual, refrain
        if skill.is_alternate:
            self.alt_tap = ceil((self.tap - 100) * skill.values[1] / 1000)
            self.alt_flick = ceil((self.flick - 100) * skill.values[1] / 1000)
            self.alt_long = ceil((self.long - 100) * skill.values[1] / 1000)
            self.alt_slide = ceil((self.slide - 100) * skill.values[1] / 1000)
            return
        if skill.is_mutual:
            self.alt_combo = ceil((self.combo - 100) * skill.values[1] / 1000)
            return
        if skill.is_refrain:
            self.ref_tap = max(self.ref_tap, self.tap - 100)
            self.ref_flick = max(self.ref_flick, self.flick - 100)
            self.ref_long = max(self.ref_long, self.long - 100)
            self.ref_slide = max(self.ref_slide, self.slide - 100)
            self.ref_combo = max(self.ref_combo, self.combo - 100)
            return


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
        self.weights = weights

        self._note_type_stack = self.notes_data.note_type.to_list()
        self._note_idx_stack = self.notes_data.index.to_list()
        self.special_note_types = list()
        for _, note in self.notes_data.iterrows():
            temp = list()
            if note.is_flick:
                temp.append(NoteType.FLICK)
            if note.is_long:
                temp.append(NoteType.LONG)
            if note.is_slide:
                temp.append(NoteType.SLIDE)
            self.special_note_types.append(temp)

        self.probabilities = [
            self.live.get_probability(_)
            for _ in range(len(self.live.unit.all_cards()))
        ]

        self._sparkle_bonus_ssr = get_sparkle_bonus(8, self.grand)
        self._sparkle_bonus_sr = get_sparkle_bonus(6, self.grand)

    def reset_machine(self, perfect=False):
        if perfect:
            self.note_time_stack = self.notes_data.sec.map(lambda x: int(x * 1E6)).to_list()
        else:
            self.note_time_stack = (self.notes_data.sec + np.random.random(len(self.notes_data)) * 0.06 - 0.03).map(
                lambda x: int(x * 1E6)).to_list()

        self.note_type_stack = self._note_type_stack.copy()
        self.note_idx_stack = self._note_idx_stack.copy()

        # List of all skill objects. Should not mutate. Original sets.
        self.reference_skills = [None]
        for _ in range(len(self.live.unit.all_cards())):
            self.reference_skills.append(None)

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
        self.max_life = self.live.get_start_life(doublelife=True)
        self.combo = 0
        self.score = 0

        # Encore stuff
        self.last_activated_skill = list()
        self.last_activated_time = list()

        # Hacky cache stuff
        self.has_skill_change = True
        self.cache_max_boosts = None
        self.cache_sum_boosts = None
        self.cache_life_bonus = 0
        self.cache_support_bonus = 0
        self.cache_score_bonus = 0
        self.cache_combo_bonus = 0
        self.cache_magics = dict()
        self.cache_non_magics = dict()
        self.cache_ls = dict()
        self.cache_act = dict()
        self.cache_alt = dict()
        self.cache_mut = dict()
        self.cache_ref = dict()
        self.cache_enc = dict()

        # Cache for AMR
        self.unit_caches = list()
        for _ in range(len(self.live.unit.all_units)):
            self.unit_caches.append(UnitCacheBonus())

        # Metrics
        self.full_roll_chance = 1
        self.note_scores = list()

    def initialize_activation_arrays(self):
        skill_times = list()
        skill_indices = list()
        for unit_idx, unit in enumerate(self.live.unit.all_units):
            iterating_order = list()
            _cache_cached_classes = list()
            _cache_magic = list()
            for card_idx, card in enumerate(unit.all_cards()):
                if card.skill.is_magic:
                    _cache_magic.append((card_idx, card))
                    continue
                if card.skill.is_alternate or card.skill.is_mutual or card.skill.is_refrain:
                    _cache_cached_classes.append((card_idx, card))
                    continue
                iterating_order.append((card_idx, card))
            iterating_order = _cache_magic + iterating_order + _cache_cached_classes
            for card_idx, card in iterating_order:
                skill = copy.copy(card.skill)
                idx = unit_idx * 5 + card_idx
                self.reference_skills[idx + 1] = skill
                if self.probabilities[idx] == 0:
                    continue
                times = int((self.notes_data.iloc[-1].sec - 3) // skill.interval)
                skill_range = list(range(skill.offset + 1, times + 1, self.unit_offset))
                for act_idx in skill_range:
                    act = act_idx * skill.interval
                    deact = act_idx * skill.interval + skill.duration
                    skill_times.append(int(act * 1E6))
                    skill_times.append(int(deact * 1E6))
                    skill_indices.append(unit_idx * 5 + card_idx + 1)
                    skill_indices.append(-unit_idx * 5 - card_idx - 1)
                self.full_roll_chance *= self.probabilities[idx] ** len(skill_range)
        np_skill_times = np.array(skill_times)
        np_skill_indices = np.array(skill_indices)
        sorted_indices = np.argsort(np_skill_times, kind='stable')
        self.skill_times = np_skill_times[sorted_indices].tolist()
        self.skill_indices = np_skill_indices[sorted_indices].tolist()

    def simulate_impl(self):
        self.initialize_activation_arrays()
        while True:
            # Terminal condition: No more skills and no more notes
            if len(self.skill_times) == 0 and len(self.note_time_stack) == 0:
                break

            if len(self.skill_times) == 0:
                self.handle_note()
            elif len(self.note_time_stack) == 0:
                self.handle_skill()
            elif self.note_time_stack[0] < self.skill_times[0]:
                self.handle_note()
            elif self.skill_times[0] < self.note_time_stack[0]:
                self.handle_skill()
            else:
                if (self.skill_indices[0] > 0 and self.left_inclusive) or \
                        (self.skill_indices[0] < 0 and not self.right_inclusive):
                    self.handle_skill()
                else:
                    self.handle_note()
        return self.score, self.life, self.combo

    def handle_skill(self):
        self.has_skill_change = True
        if self.skill_indices[0] > 0:
            if not self._expand_encore():
                return
            self._expand_magic()
            self._handle_skill_activation()
            # By this point, all skills that can be activated should be in self.skill_queue
            self._evaluate_motif()
            self._evaluate_ls()
            self._cache_skill_data()
            self._cache_AMR()
            self.skill_indices.pop(0)
            self.skill_times.pop(0)
        else:
            self.skill_queue.pop(-self.skill_indices[0])
            self.skill_indices.pop(0)
            self.skill_times.pop(0)

    def handle_note(self):
        note_time = self.note_time_stack.pop(0)
        note_type = self.note_type_stack.pop(0)
        note_idx = self.note_idx_stack.pop(0)
        weight = self.weights[self.combo]
        self.combo += 1
        score_bonus, combo_bonus = self.evaluate_bonuses(self.special_note_types[note_idx])
        note_score = round(self.base_score * weight * (1 + combo_bonus / 100) * (1 + score_bonus / 100))
        self.note_scores.append(note_score)
        self.score += note_score
        self.has_skill_change = False

    def evaluate_bonuses(self, special_note_types):
        if self.has_skill_change:
            magics = dict()
            non_magics = dict()
            for skill_idx, skills in self.skill_queue.items():
                if self.live.unit.get_card(skill_idx - 1).skill.is_magic:
                    magics[skill_idx] = skills
                else:
                    non_magics[skill_idx] = skills
            self.cache_magics = magics
            self.cache_non_magics = non_magics
        else:
            magics = self.cache_magics
            non_magics = self.cache_non_magics
        max_boosts, sum_boosts = self._evaluate_bonuses_phase_boost(magics, non_magics)
        life_bonus, support_bonus = self._evaluate_bonuses_phase_life_support(magics, non_magics, max_boosts,
                                                                              sum_boosts)
        self.life += life_bonus
        self.life = min(self.max_life, self.life)  # Cap life
        self._helper_evaluate_ls()
        self._helper_evaluate_act(special_note_types)
        self._helper_evaluate_alt_mutual_ref(special_note_types)
        self._helper_normalize_score_combo_bonuses()
        score_bonus, combo_bonus = self._evaluate_bonuses_phase_score_combo(magics, non_magics, max_boosts, sum_boosts)
        return score_bonus, combo_bonus

    def _helper_evaluate_ls(self):
        trimmed_life = self.life // 10
        for idx, skills in self.skill_queue.items():
            for skill in skills:
                if skill.is_sparkle:
                    if skill.values[0] == 1:
                        skill.v1 = self._sparkle_bonus_ssr[trimmed_life] - 100
                    else:
                        skill.v1 = self._sparkle_bonus_sr[trimmed_life] - 100
                    if idx not in self.cache_ls or self.cache_ls[idx] != skill.v1:
                        self.has_skill_change = True
                    self.cache_act[idx] = skill.v1
                    skill.v0 = 0
                    skill.normalized = True

    def _helper_evaluate_act(self, special_note_types):
        for idx, skills in self.skill_queue.items():
            for skill in skills:
                if skill.act is not None:
                    if skill.act in special_note_types:
                        skill.v0 = skill.values[1]
                        skill.v1 = 0
                    else:
                        skill.v0 = skill.values[0]
                        skill.v1 = 0
                    if idx not in self.cache_act or self.cache_act[idx] != skill.v0:
                        self.has_skill_change = True
                    self.cache_act[idx] = skill.v0
                    skill.normalized = False

    def _helper_normalize_score_combo_bonuses(self):
        for idx, skills in self.skill_queue.items():
            for skill in skills:
                if skill.boost or skill.normalized:
                    continue
                if skill.v0 > 0:
                    skill.v0 -= 100
                if skill.v1 > 0:
                    skill.v1 -= 100
                skill.normalized = True

    def _helper_evaluate_alt_mutual_ref(self, special_note_types):
        for idx, skills in self.skill_queue.items():
            unit_idx = (idx - 1) // 5
            for skill in skills:
                if skill.is_alternate:
                    skill.v1 = skill.values[0] - 100
                    skill.v0 = self.unit_caches[unit_idx].alt_tap
                    if NoteType.FLICK in special_note_types:
                        skill.v0 = max(skill.v0, self.unit_caches[unit_idx].alt_tap)
                    if NoteType.LONG in special_note_types:
                        skill.v0 = max(skill.v0, self.unit_caches[unit_idx].alt_long)
                    if NoteType.SLIDE in special_note_types:
                        skill.v0 = max(skill.v0, self.unit_caches[unit_idx].alt_slide)
                    if idx not in self.cache_alt or self.cache_alt[idx] != skill.v0:
                        self.has_skill_change = True
                    self.cache_alt[idx] = skill.v0
                    skill.normalized = True
                    continue
                if skill.is_mutual:
                    skill.v0 = skill.values[0] - 100
                    skill.v1 = self.unit_caches[unit_idx].alt_combo
                    if idx not in self.cache_mut or self.cache_mut[idx] != skill.v1:
                        self.has_skill_change = True
                    self.cache_mut[idx] = skill.v1
                    skill.normalized = True
                    continue
                if skill.is_refrain:
                    skill.v0 = self.unit_caches[unit_idx].ref_tap
                    if NoteType.FLICK in special_note_types:
                        skill.v0 = max(skill.v0, self.unit_caches[unit_idx].ref_tap)
                    if NoteType.LONG in special_note_types:
                        skill.v0 = max(skill.v0, self.unit_caches[unit_idx].ref_long)
                    if NoteType.SLIDE in special_note_types:
                        skill.v0 = max(skill.v0, self.unit_caches[unit_idx].ref_slide)
                    skill.v1 = self.unit_caches[unit_idx].ref_combo
                    if idx not in self.cache_ref \
                            or self.cache_ref[idx][0] != skill.v0 or self.cache_ref[idx][1] != skill.v1:
                        self.has_skill_change = True
                    self.cache_ref[idx] = (skill.v0, skill.v1)
                    skill.normalized = True
                    continue

    def _evaluate_bonuses_phase_boost(self, magics: Dict[int, List[Skill]], non_magics: Dict[int, List[Skill]]):
        if not self.has_skill_change:
            return self.cache_max_boosts, self.cache_sum_boosts

        magic_boosts = [
            # Score, Combo, Life, Support
            [1000, 1000, 1000, 0],  # Cute
            [1000, 1000, 1000, 0],  # Cool
            [1000, 1000, 1000, 0]  # Passion
        ]
        for magic_idx, skills in magics.items():
            for skill in skills:
                if not skill.boost:
                    continue
                for target in skill.targets:
                    for _ in range(4):
                        magic_boosts[target][_] = max(magic_boosts[target][_], skill.values[_])

        max_boosts = [
            [1000, 1000, 1000, 0],
            [1000, 1000, 1000, 0],
            [1000, 1000, 1000, 0]
        ]
        sum_boosts = [
            [1000, 1000, 1000, 0],
            [1000, 1000, 1000, 0],
            [1000, 1000, 1000, 0]
        ]

        for non_magic_idx, skills in non_magics.items():
            assert len(skills) == 1 \
                   or self.reference_skills[non_magic_idx].is_encore \
                   and self.reference_skills[self.cache_enc[non_magic_idx]].is_magic
            for skill in skills:
                if not skill.boost:
                    continue
                for target in skill.targets:
                    for _ in range(4):
                        if skill.values[_] == 0:
                            continue
                        max_boosts[target][_] = max(max_boosts[target][_], skill.values[_])
                        if _ == 3:
                            sum_boosts[target][_] = sum_boosts[target][_] + skill.values[_]
                        else:
                            sum_boosts[target][_] = sum_boosts[target][_] + skill.values[_] - 1000
        for i in range(3):
            for j in range(4):
                max_boosts[i][j] = max(max_boosts[i][j], magic_boosts[i][j])
                sum_boosts[i][j] = sum_boosts[i][j] + magic_boosts[i][j]
                if j < 3:
                    sum_boosts[i][j] -= 1000
        # Normalize boosts
        for i in range(3):
            for j in range(3):
                max_boosts[i][j] /= 1000
                sum_boosts[i][j] /= 1000
        self.cache_max_boosts = max_boosts
        self.cache_sum_boosts = sum_boosts
        return max_boosts, sum_boosts

    def _evaluate_bonuses_phase_life_support(self, magics: Dict[int, List[Skill]], non_magics: Dict[int, List[Skill]],
                                             max_boosts, sum_boosts):
        if not self.has_skill_change:
            return self.cache_life_bonus, self.cache_support_bonus
        temp_life_results = dict()
        temp_support_results = dict()
        for magic_idx, skills in magics.items():
            magic_idx = magic_idx - 1
            temp_life_results[magic_idx] = 0
            temp_support_results[magic_idx] = 0
            unit_idx = magic_idx // 5
            boost_dict = sum_boosts if self.live.unit.all_units[unit_idx].resonance else max_boosts
            for skill in skills:
                if skill.boost:
                    continue
                color = int(self.live.unit.get_card(magic_idx).color.value)
                if skill.v2 == 0 and skill.v3 == 0:
                    continue
                if skill.v2 > 0:
                    temp_life_results[magic_idx] = max(temp_life_results[magic_idx],
                                                       ceil(skill.v2 * boost_dict[color][2]))
                if skill.v3 > 0:
                    temp_support_results[magic_idx] = max(temp_support_results[magic_idx],
                                                          ceil(skill.v3 + boost_dict[color][3]))
        for non_magic_idx, skills in non_magics.items():
            assert len(skills) == 1 \
                   or self.reference_skills[non_magic_idx].is_encore \
                   and self.reference_skills[self.cache_enc[non_magic_idx]].is_magic
            for skill in skills:
                if skill.boost:
                    continue
                non_magic_idx = non_magic_idx - 1
                color = int(self.live.unit.get_card(non_magic_idx).color.value)
                unit_idx = non_magic_idx // 5
                boost_dict = sum_boosts if self.live.unit.all_units[unit_idx].resonance else max_boosts
                if skill.v2 == 0 and skill.v3 == 0:
                    continue
                if skill.v2 > 0:
                    temp_life_results[non_magic_idx] = ceil(skill.v2 * boost_dict[color][2])
                if skill.v3 > 0:
                    temp_support_results[non_magic_idx] = ceil(skill.v3 + boost_dict[color][3])

        unit_life_bonuses = list()
        unit_support_bonuses = list()
        for unit_idx in range(len(self.live.unit.all_units)):
            agg_func = sum if self.live.unit.all_units[unit_idx].resonance else max

            unit_magics = {_ - 1 for _ in magics.keys() if unit_idx * 5 < _ <= unit_idx * 5 + 5}
            unit_non_magics = {_ - 1 for _ in non_magics.keys() if unit_idx * 5 < _ <= unit_idx * 5 + 5}
            # Unify magic
            unified_magic_life = 0
            unified_magic_support = 0
            unified_non_magic_life = 0
            unified_non_magic_support = 0
            if len(unit_magics) >= 1:
                for magic_idx in unit_magics:
                    if magic_idx in temp_life_results:
                        unified_magic_life = max((unified_magic_life, temp_life_results[magic_idx]))
                    if magic_idx in temp_support_results:
                        unified_magic_support = max((unified_magic_support, temp_support_results[magic_idx]))
            for non_magic in unit_non_magics:
                if non_magic in temp_life_results:
                    unified_non_magic_life = agg_func((unified_non_magic_life, temp_life_results[non_magic]))
                if non_magic in temp_support_results:
                    unified_non_magic_support = agg_func((unified_non_magic_support, temp_support_results[non_magic]))
            unit_life_bonuses.append(agg_func((unified_magic_life, unified_non_magic_life)))
            unit_support_bonuses.append(agg_func((unified_magic_support, unified_non_magic_support)))
        self.cache_life_bonus = max(unit_life_bonuses)
        self.cache_support_bonus = max(unit_support_bonuses)
        return self.cache_life_bonus, self.cache_support_bonus

    def _evaluate_bonuses_phase_score_combo(self, magics: Dict[int, List[Skill]], non_magics: Dict[int, List[Skill]],
                                            max_boosts, sum_boosts):
        if not self.has_skill_change:
            return self.cache_score_bonus, self.cache_combo_bonus
        temp_score_results = dict()
        temp_combo_results = dict()
        for magic_idx, skills in magics.items():
            magic_idx = magic_idx - 1
            temp_score_results[magic_idx] = None
            temp_combo_results[magic_idx] = None
            unit_idx = magic_idx // 5
            boost_dict = sum_boosts if self.live.unit.all_units[unit_idx].resonance else max_boosts
            for skill in skills:
                if skill.boost:
                    continue
                color = int(self.live.unit.get_card(magic_idx).color.value)
                if skill.v0 == 0 and skill.v1 == 0:
                    continue
                if temp_score_results[magic_idx] is None:
                    temp_score_results[magic_idx] = ceil(skill.v0 * boost_dict[color][0])
                else:
                    temp_score_results[magic_idx] = max(temp_score_results[magic_idx],
                                                        ceil(skill.v0 * boost_dict[color][0]))
                if temp_combo_results[magic_idx] is None:
                    temp_combo_results[magic_idx] = ceil(skill.v1 * boost_dict[color][1])
                else:
                    temp_combo_results[magic_idx] = max(temp_combo_results[magic_idx],
                                                        ceil(skill.v1 * boost_dict[color][1]))
            if temp_score_results[magic_idx] is None:
                temp_score_results[magic_idx] = 0
            if temp_combo_results[magic_idx] is None:
                temp_combo_results[magic_idx] = 0
        for non_magic_idx, skills in non_magics.items():
            assert len(skills) == 1 \
                   or self.reference_skills[non_magic_idx].is_encore \
                   and self.reference_skills[self.cache_enc[non_magic_idx]].is_magic
            for skill in skills:
                if skill.boost:
                    continue
                non_magic_idx = non_magic_idx - 1
                color = int(self.live.unit.get_card(non_magic_idx).color.value)
                unit_idx = non_magic_idx // 5
                boost_dict = sum_boosts if self.live.unit.all_units[unit_idx].resonance else max_boosts
                if skill.v0 == 0 and skill.v1 == 0:
                    continue
                if skill.v0 > 0:
                    temp_score_results[non_magic_idx] = ceil(skill.v0 * boost_dict[color][0])
                elif skill.v0 < 0:
                    temp_score_results[non_magic_idx] = skill.v0
                if skill.v1 > 0:
                    temp_combo_results[non_magic_idx] = ceil(skill.v1 * boost_dict[color][1])
                elif skill.v1 < 0:
                    temp_combo_results[non_magic_idx] = skill.v1

        unit_score_bonuses = list()
        unit_combo_bonuses = list()
        for unit_idx in range(len(self.live.unit.all_units)):
            agg_func = sum if self.live.unit.all_units[unit_idx].resonance else max

            unit_magics = {_ - 1 for _ in magics.keys() if unit_idx * 5 < _ <= unit_idx * 5 + 5}
            unit_non_magics = {_ - 1 for _ in non_magics.keys() if unit_idx * 5 < _ <= unit_idx * 5 + 5}
            # Unify magic
            unified_magic_score = None
            unified_magic_combo = None
            unified_non_magic_score = None
            unified_non_magic_combo = None
            if len(unit_magics) >= 1:
                for magic_idx in unit_magics:
                    if magic_idx in temp_score_results:
                        if unified_magic_score is None:
                            unified_magic_score = temp_score_results[magic_idx]
                        else:
                            unified_magic_score = max((unified_magic_score, temp_score_results[magic_idx]))
                    if magic_idx in temp_combo_results:
                        if unified_magic_combo is None:
                            unified_magic_combo = temp_combo_results[magic_idx]
                        else:
                            unified_magic_combo = max((unified_magic_combo, temp_combo_results[magic_idx]))
            if unified_magic_score is None:
                unified_magic_score = 0
            if unified_magic_combo is None:
                unified_magic_combo = 0
            for non_magic in unit_non_magics:
                if non_magic in temp_score_results:
                    if unified_non_magic_score is None:
                        unified_non_magic_score = temp_score_results[non_magic]
                    else:
                        unified_non_magic_score = agg_func((unified_non_magic_score, temp_score_results[non_magic]))
                if non_magic in temp_combo_results:
                    if unified_non_magic_combo is None:
                        unified_non_magic_combo = temp_combo_results[non_magic]
                    else:
                        unified_non_magic_combo = agg_func((unified_non_magic_combo, temp_combo_results[non_magic]))
            if unified_non_magic_score is None:
                unified_non_magic_score = 0
            if unified_non_magic_combo is None:
                unified_non_magic_combo = 0
            unit_score_bonuses.append(agg_func((unified_magic_score, unified_non_magic_score)))
            unit_combo_bonuses.append(agg_func((unified_magic_combo, unified_non_magic_combo)))
        min_score_bonus = min(unit_score_bonuses)
        max_score_bonus = max(unit_score_bonuses)
        min_combo_bonus = min(unit_combo_bonuses)
        max_combo_bonus = max(unit_combo_bonuses)
        self.cache_score_bonus = max_score_bonus if max_score_bonus > 0 else min_score_bonus
        self.cache_combo_bonus = max_combo_bonus if max_combo_bonus > 0 else min_combo_bonus
        return self.cache_score_bonus, self.cache_combo_bonus

    def _expand_magic(self):
        skill = self.reference_skills[self.skill_indices[0]]
        if skill.is_magic or \
                (skill.is_encore and self.skill_queue[self.skill_indices[0]].is_magic):
            if skill.is_magic:
                unit_idx = (self.skill_indices[0] - 1) // 5
            else:
                unit_idx = (self.cache_enc[self.skill_indices[0]] - 1) // 5
            self.skill_queue[self.skill_indices[0]] = list()
            iterating_order = list()
            _cache_cached_classes = list()
            for idx in range(unit_idx * 5, unit_idx * 5 + 5):
                idx = idx + 1
                copied_skill = copy.deepcopy(self.reference_skills[idx])
                # Skip skills that cannot activate
                if self.reference_skills[idx].probability == 0:
                    continue
                # Magic does not copy itself
                if self.reference_skills[idx].is_magic:
                    continue
                # Expand encore
                if self.reference_skills[idx].is_encore:
                    copied_skill = self._get_last_encoreable_skill()
                    # But there's nothing for encore to copy yet, skip
                    if copied_skill is None:
                        continue
                    # Or the skill for encore to copy is magic as well, skip
                    # Do not allow magic-encore-magic
                    copied_skill = self.reference_skills[copied_skill]
                    if copied_skill.is_magic:
                        continue
                    # Else let magic copy the encored skill instead
                if copied_skill.is_alternate or copied_skill.is_mutual or copied_skill.is_refrain:
                    _cache_cached_classes.append(copied_skill)
                    continue
                iterating_order.append(copied_skill)
            iterating_order = iterating_order + _cache_cached_classes
            for _ in iterating_order:
                self.skill_queue[self.skill_indices[0]].append(_)

    def _expand_encore(self):
        skill = self.reference_skills[self.skill_indices[0]]
        if skill.is_encore:
            last_encoreable_skill = self._get_last_encoreable_skill()
            if last_encoreable_skill is None:
                pop_skill_index = self.skill_indices.index(-self.skill_indices[0])
                self.skill_times.pop(pop_skill_index)
                self.skill_indices.pop(pop_skill_index)
                self.skill_indices.pop(0)
                self.skill_times.pop(0)
                return False
            encore_copy: Skill = copy.deepcopy(self.reference_skills[last_encoreable_skill])
            encore_copy.interval = skill.interval
            encore_copy.duration = skill.duration
            self.skill_queue[self.skill_indices[0]] = encore_copy
            self.cache_enc[self.skill_indices[0]] = last_encoreable_skill
        return True

    def _get_last_encoreable_skill(self):
        if len(self.last_activated_skill) == 0:
            return None
        if self.skill_times[0] > self.last_activated_time[-1]:
            return self.last_activated_skill[-1]
        elif len(self.last_activated_time) == 1:
            return None
        else:
            return self.last_activated_skill[-2]

    def _evaluate_motif(self):
        skills_to_check = self._helper_get_current_skills()
        unit_idx = (self.skill_indices[0] - 1) // 5
        for skill in skills_to_check:
            if skill.is_motif:
                skill.v0 = self.live.unit.all_units[unit_idx].convert_motif(skill.skill_type, self.grand)
                skill.normalized = False

    def _evaluate_ls(self):
        skills_to_check = self._helper_get_current_skills()
        for skill in skills_to_check:
            if skill.is_sparkle:
                trimmed_life = self.life // 10
                if skill.values[0] == 1:
                    skill.v1 = self._sparkle_bonus_ssr[trimmed_life]
                else:
                    skill.v1 = self._sparkle_bonus_sr[trimmed_life]
                skill.v0 = 0

    def _cache_AMR(self):
        skills_to_check = self._helper_get_current_skills()
        unit_idx = (self.skill_indices[0] - 1) // 5
        for skill in skills_to_check:
            if skill.is_alternate or skill.is_mutual or skill.is_refrain:
                self.unit_caches[unit_idx].update_AMR(skill)

    def _helper_get_current_skills(self):
        if self.skill_indices[0] not in self.skill_queue:
            return []
        skills_to_check = self.skill_queue[self.skill_indices[0]]
        if isinstance(skills_to_check, Skill):
            skills_to_check = [skills_to_check]
        return skills_to_check

    def _cache_skill_data(self):
        skills_to_check = self._helper_get_current_skills()
        unit_idx = (self.skill_indices[0] - 1) // 5
        for skill in skills_to_check:
            self.unit_caches[unit_idx].update(skill)

    def _handle_skill_activation(self):
        def update_last_activated_skill(replace, skill_time):
            """
            Update last activated skill for encore
            :type replace: True if new skill activates after the cached skill, False if same time
            """
            if self.reference_skills[self.skill_indices[0]].is_encore:
                return
            if replace:
                self.last_activated_skill.append(self.skill_indices[0])
                self.last_activated_time.append(skill_time)
            else:
                self.last_activated_skill[-1] = min(self.last_activated_skill[-1], self.skill_indices[0])

        # If skill is still not queued after self._expand_magic and self._expand_encore
        if self.skill_indices[0] not in self.skill_queue:
            self.skill_queue[self.skill_indices[0]] = self.reference_skills[self.skill_indices[0]]

        # Pop deactivation out if skill cannot activate
        if not self._can_activate():
            skill_id = self.skill_indices[0]
            self.skill_queue.pop(self.skill_indices[0])
            # First index of -skill_id should be the correct value because a skill cannot activate twice before deactivating once
            pop_skill_index = self.skill_indices.index(-skill_id)
            # Pop the deactivation first to avoid messing up the index
            self.skill_times.pop(pop_skill_index)
            self.skill_indices.pop(pop_skill_index)
            # Don't need to pop the activation because it will be pop in the outer sub
            return

        # Update last activated skill for encore
        # If new skill is strictly after cached last skill, just replace it
        if len(self.last_activated_time) == 0 or self.last_activated_time[-1] < self.skill_times[0]:
            update_last_activated_skill(replace=True, skill_time=self.skill_times[0])
        elif self.last_activated_time == self.skill_times[0]:
            # Else update taking skill index order into consideration
            update_last_activated_skill(replace=False, skill_time=self.skill_times[0])

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
        unit_idx = (self.skill_indices[0] - 1) // 5
        skills_to_check = self.skill_queue[self.skill_indices[0]]
        if isinstance(skills_to_check, Skill):
            skills_to_check = [skills_to_check]
        has_failed = False
        to_be_removed = list()
        for skill in skills_to_check:
            if has_failed and skill.is_overload:
                to_be_removed.append(skill)
                continue
            if not has_failed and skill.is_overload:
                has_failed = self._handle_ol_drain(skill.life_requirement)
                if has_failed:
                    to_be_removed.append(skill)
                continue
            if skill.is_encore:
                # Encore should not be here, all encores should have already been replaced
                to_be_removed.append(skill)
                continue
            if skill.is_alternate and self.unit_caches[unit_idx].tap == 0:
                to_be_removed.append(skill)
                continue
            if skill.is_mutual and self.unit_caches[unit_idx].combo == 0:
                to_be_removed.append(skill)
                continue
            if skill.is_refrain and self.unit_caches[unit_idx].tap == 0 and self.unit_caches[unit_idx].combo == 0:
                to_be_removed.append(skill)
                continue
            if skill.is_focus:
                if not self._check_focus_activation(unit_idx=self.skill_indices[0] // 5, skill=skill):
                    to_be_removed.append(skill)
                continue
        for skill in to_be_removed:
            skills_to_check.remove(skill)
        self.skill_queue[self.skill_indices[0]] = skills_to_check
        return len(skills_to_check) > 0

import copy
from math import ceil
from random import random
from typing import Dict, Union, List, Tuple

import cython
import numpy as np
import pandas as pd

from logic.live import BaseLive
from logic.skill import Skill
from static.color import Color
from static.judgement import Judgement
from static.note_type import NoteType
from static.skill import get_sparkle_bonus
from static.song_difficulty import PERFECT_TAP_RANGE, GREAT_TAP_RANGE, Difficulty


@cython.cclass
class UnitCacheBonus:
    tap: int
    flick: int
    longg: int
    slide: int
    combo: int
    ref_tap: int
    ref_flick: int
    ref_long: int
    ref_slide: int
    ref_combo: int
    alt_tap: int
    alt_flick: int
    alt_long: int
    alt_slide: int
    alt_combo: int

    def __init__(self):
        self.tap = 0
        self.flick = 0
        self.longg = 0
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
                self.longg = max(self.longg, skill.values[1])
                self.flick = max(self.flick, skill.values[0])
                self.slide = max(self.slide, skill.values[0])
            elif skill.act is NoteType.FLICK:
                self.longg = max(self.longg, skill.values[0])
                self.flick = max(self.flick, skill.values[1])
                self.slide = max(self.slide, skill.values[0])
            elif skill.act is NoteType.SLIDE:
                self.longg = max(self.longg, skill.values[0])
                self.flick = max(self.flick, skill.values[0])
                self.slide = max(self.slide, skill.values[1])
            return
        if skill.v0 is not None and skill.v0 > 100:
            self.tap = max(self.tap, skill.v0)
            self.flick = max(self.flick, skill.v0)
            self.longg = max(self.longg, skill.v0)
            self.slide = max(self.slide, skill.v0)
        if skill.v1 is not None and skill.v1 > 100:
            self.combo = max(self.combo, skill.v1)

    def update_AMR(self, skill: Skill):
        # Do not update on skills that are not alternate, mutual, refrain
        if skill.is_alternate:
            self.alt_tap = ceil((self.tap - 100) * skill.values[1] / 1000)
            self.alt_flick = ceil((self.flick - 100) * skill.values[1] / 1000)
            self.alt_long = ceil((self.longg - 100) * skill.values[1] / 1000)
            self.alt_slide = ceil((self.slide - 100) * skill.values[1] / 1000)
            return
        if skill.is_mutual:
            self.alt_combo = ceil((self.combo - 100) * skill.values[1] / 1000)
            return
        if skill.is_refrain:
            self.ref_tap = max(self.ref_tap, self.tap - 100)
            self.ref_flick = max(self.ref_flick, self.flick - 100)
            self.ref_long = max(self.ref_long, self.longg - 100)
            self.ref_slide = max(self.ref_slide, self.slide - 100)
            self.ref_combo = max(self.ref_combo, self.combo - 100)
            return


@cython.cclass
class StateMachine:
    left_inclusive: int
    right_inclusive: int
    fail_simulate: bool
    perfect_only: bool

    grand: bool
    difficulty: Difficulty
    doublelife: bool
    live: BaseLive
    notes_data: pd.DataFrame
    base_score: float
    helen_base_score: float

    unit_offset: int
    weights: List[int]

    _note_type_stack: List[NoteType]
    _note_idx_stack: List[int]
    _special_note_types: List[List[NoteType]]

    probabilities: List[float]

    _sparkle_bonus_ssr: List[int]
    _sparkle_bonus_sr: List[int]

    note_time_stack: List[int]
    note_time_deltas: List[int]
    note_type_stack: List[NoteType]
    special_note_types: List[List[NoteType]]
    note_idx_stack: List[int]
    checkpoints: List[bool]

    skill_times: List[int]
    skill_indices: List[int]
    skill_queue: Dict[int, Union[Skill, List[Skill]]]
    reference_skills: List[Skill]

    life: int
    max_life: int
    combo: int
    combos: List[int]
    score_bonuses: List[int]
    combo_bonuses: List[int]
    judgements: List[Judgement]
    note_scores: np.ndarray
    np_score_bonuses: np.ndarray
    np_combo_bonuses: np.ndarray
    cache_perfect_score_array: np.ndarray

    last_activated_skill: List[int]
    last_activated_time: List[int]

    has_skill_change: bool
    cache_max_boosts: List[List[int]]
    cache_sum_boosts: List[List[int]]
    cache_life_bonus: int
    cache_support_bonus: int
    cache_score_bonus: int
    cache_combo_bonus: int
    cache_magics: Dict[int, Union[Skill, List[Skill]]]
    cache_non_magics: Dict[int, Union[Skill, List[Skill]]]
    cache_ls: Dict[int, int]
    cache_act: Dict[int, int]
    cache_alt: Dict[int, int]
    cache_mut: Dict[int, int]
    cache_ref: Dict[int, Tuple[int, int]]
    cache_enc: Dict[int, int]

    abuse: bool
    is_abuse: List[bool]
    note_time_deltas_backup: List[int]
    note_idx_stack_backup: List[int]
    is_abuse_backup: List[bool]

    unit_caches: List[UnitCacheBonus]
    full_roll_chance: float
    has_cc: bool

    def __init__(self, grand, difficulty, doublelife, live, notes_data, left_inclusive, right_inclusive, base_score,
                 helen_base_score, weights):
        self.left_inclusive = left_inclusive
        self.right_inclusive = right_inclusive

        self.grand = grand
        self.difficulty = difficulty
        self.doublelife = doublelife
        self.live = live
        self.notes_data = notes_data
        self.base_score = base_score
        self.helen_base_score = helen_base_score

        self.unit_offset = 3 if grand else 1
        self.weights = weights

        self._note_type_stack = self.notes_data.note_type.to_list()
        self._note_idx_stack = self.notes_data.index.to_list()
        self._special_note_types = list()
        for _, note in self.notes_data.iterrows():
            temp = list()
            if note.is_flick:
                temp.append(NoteType.FLICK)
            if note.is_long:
                temp.append(NoteType.LONG)
            if note.is_slide:
                temp.append(NoteType.SLIDE)
            self._special_note_types.append(temp)
        self.checkpoints = self.notes_data["checkpoints"].to_list()

        self.probabilities = [
            self.live.get_probability(_)
            for _ in range(len(self.live.unit.all_cards()))
        ]

        self._sparkle_bonus_ssr = get_sparkle_bonus(8, self.grand)
        self._sparkle_bonus_sr = get_sparkle_bonus(6, self.grand)

        self.has_cc = any([
            card.skill.is_cc
            for card in self.live.unit.all_cards()
        ])

        # Abuse stuff
        self.abuse = False
        self.is_abuse = [False] * len(self.notes_data)
        self.cache_perfect_score_array = None

    def get_note_scores(self):
        return self.note_scores

    def get_full_roll_chance(self):
        return self.full_roll_chance

    def reset_machine(self, perfect_play=False, perfect_only=True, abuse=False):
        if not perfect_only:
            assert not perfect_play

        self.fail_simulate = not perfect_play
        self.perfect_only = perfect_only
        self.abuse = abuse

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
        self.combos = list()
        self.score_bonuses = list()
        self.combo_bonuses = list()
        self.judgements = list()

        self.note_scores = None
        self.np_score_bonuses = None
        self.np_combo_bonuses = None

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

        # Initializing note data
        if abuse or perfect_play:
            self.note_time_stack = self.notes_data.sec.map(lambda x: int(x * 1E6)).to_list()
            self.note_time_deltas = [0] * len(self.note_time_stack)
            self.note_type_stack = self._note_type_stack.copy()
            self.note_idx_stack = self._note_idx_stack.copy()
            self.special_note_types = self._special_note_types.copy()
            if abuse:
                self.initialize_activation_arrays()
                self._helper_fill_abuse_dummies()
        else:
            random_range = PERFECT_TAP_RANGE[self.difficulty] / 2E6 \
                if perfect_only else GREAT_TAP_RANGE[self.difficulty] / 2E6

            temp = self.notes_data.sec + np.random.random(len(self.notes_data)) * 2 * random_range - random_range
            temp[self.notes_data["checkpoints"]] = np.maximum(
                temp[self.notes_data["checkpoints"]],
                self.notes_data.loc[self.notes_data["checkpoints"], "sec"])
            temp_note_time_deltas = (temp - self.notes_data.sec).map(lambda x: int(x * 1E6))
            temp_note_time_stack = temp.map(lambda x: int(x * 1E6))
            sorted_indices = np.argsort(temp_note_time_stack)
            self.note_time_stack = temp_note_time_stack[sorted_indices].tolist()
            self.note_time_deltas = temp_note_time_deltas[sorted_indices].tolist()
            self.note_type_stack = [self._note_type_stack[_] for _ in sorted_indices]
            self.note_idx_stack = [self._note_idx_stack[_] for _ in sorted_indices]
            self.special_note_types = [self._special_note_types[_] for _ in sorted_indices]

    def _helper_fill_abuse_dummies(self):
        # Abuse should be the last stage of a simulation pipeline
        assert len(self.checkpoints) == len(self.notes_data)

        def get_range(note_type_internal, checkpoint_internal):
            if note_type_internal == NoteType.TAP:
                l_g = -GREAT_TAP_RANGE[self.live.difficulty]
                l_p = -PERFECT_TAP_RANGE[self.live.difficulty]
                r_g = GREAT_TAP_RANGE[self.live.difficulty]
                r_p = PERFECT_TAP_RANGE[self.live.difficulty]
                return (l_g, r_g), (l_g, l_p, r_p, r_g)
            elif note_type_internal == NoteType.FLICK or note_type_internal == NoteType.LONG:
                l_g = -180000
                l_p = -150000
                r_g = 180000
                r_p = 150000
                return (l_g, r_g), (l_g, l_p, r_p, r_g)
            elif not checkpoint_internal:
                l_p = -200000
                r_p = 200000
                return (l_p, r_p), (l_p, r_p)
            else:
                r_p = 200000
                return (0, r_p), (r_p,)

        for note_time, note_time_delta, note_type, note_idx, special_note_types, checkpoint, weight in zip(
                self.note_time_stack[:],
                self.note_time_deltas[:],
                self.note_type_stack[:],
                self.note_idx_stack[:],
                self.special_note_types[:],
                self.checkpoints[:],
                self.weights[:]
        ):
            boundaries, deltas = get_range(note_type, checkpoint)
            for delta in deltas:
                dummy_range = [delta]
                if self.has_cc and delta != 0:
                    dummy_range.append(delta // 2)
                for _ in dummy_range:
                    self.note_time_stack.append(note_time + _)
                    self.note_time_deltas.append(_)
                    self.note_type_stack.append(note_type)
                    self.note_idx_stack.append(note_idx)
                    self.special_note_types.append(special_note_types)
                    self.checkpoints.append(checkpoint)
                    self.is_abuse.append(True)
                    self.weights.append(weight)
            left, right = boundaries
            left = note_time + left
            right = note_time + right
            for skill_time in self.skill_times:
                for d in [-1, 0, 1]:
                    test_skill_time = skill_time + d
                    if test_skill_time > right:
                        break
                    if test_skill_time < left:
                        continue
                    if test_skill_time == note_time:
                        continue
                    delta = test_skill_time - note_time
                    self.note_time_stack.append(test_skill_time)
                    self.note_time_deltas.append(delta)
                    self.note_type_stack.append(note_type)
                    self.note_idx_stack.append(note_idx)
                    self.special_note_types.append(special_note_types)
                    self.checkpoints.append(checkpoint)
                    self.is_abuse.append(True)
                    self.weights.append(weight)

        sorted_indices = np.argsort(self.note_time_stack)
        self.note_time_stack = [self.note_time_stack[_] for _ in sorted_indices]
        self.note_time_deltas = [self.note_time_deltas[_] for _ in sorted_indices]
        self.note_type_stack = [self.note_type_stack[_] for _ in sorted_indices]
        self.note_idx_stack = [self.note_idx_stack[_] for _ in sorted_indices]
        self.special_note_types = [self.special_note_types[_] for _ in sorted_indices]
        self.checkpoints = [self.checkpoints[_] for _ in sorted_indices]
        self.is_abuse = [self.is_abuse[_] for _ in sorted_indices]
        self.weights = [self.weights[_] for _ in sorted_indices]

        self.note_time_deltas_backup = self.note_time_deltas.copy()
        self.note_idx_stack_backup = self.note_idx_stack.copy()
        self.is_abuse_backup = self.is_abuse.copy()

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
                    if self.probabilities[idx] < 1 and self.fail_simulate:
                        if random() > self.probabilities[idx]:
                            continue
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

    def simulate_impl(self, skip_activation_initialization=False) -> Tuple[int, List[int]]:
        if not skip_activation_initialization:
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

        # note_score = round(self.base_score * weight * (1 + combo_bonus / 100) * (1 + score_bonus / 100))

        self.np_score_bonuses = 1 + np.array(self.score_bonuses) / 100
        self.np_combo_bonuses = 1 + np.array(self.combo_bonuses) / 100

        if self.abuse or (self.fail_simulate and not self.perfect_only):
            judgement_multipliers = np.array([
                1 if x is Judgement.PERFECT
                else
                0.7 if x is Judgement.GREAT
                else 0
                for x in self.judgements])
            final_bonus = judgement_multipliers
            mask = final_bonus == 1
            if len(mask) > 0:
                final_bonus[mask] *= self.np_score_bonuses[mask]
            final_bonus[1:] *= self.np_combo_bonuses[1:]
        else:
            judgement_multipliers = 1
            final_bonus = judgement_multipliers
            final_bonus *= self.np_score_bonuses
            final_bonus[1:] *= self.np_combo_bonuses[1:]

        self.note_scores = np.round(
            self.base_score
            * np.array(self.weights)
            * final_bonus
        )

        if not self.fail_simulate and not self.abuse:
            self.cache_perfect_score_array = self.note_scores.copy()

        if self.abuse:
            assert self.cache_perfect_score_array is not None
            return self._handle_abuse_results()
        else:
            return int(self.note_scores.sum()), self.note_scores.tolist()

    def _handle_abuse_results(self):
        left_windows = [2E9] * len(self.notes_data)
        right_windows = [-2E9] * len(self.notes_data)
        max_score: List[int] = self.cache_perfect_score_array.tolist()
        is_abuses = [False] * len(self.notes_data)
        for _, (delta, note_idx, score, is_abuse) in enumerate(zip(
                self.note_time_deltas_backup,
                self.note_idx_stack_backup,
                self.note_scores,
                self.is_abuse_backup)):
            if score < max_score[note_idx]:
                continue
            if score > max_score[note_idx]:
                max_score[note_idx] = score
                is_abuses[note_idx] = is_abuses[note_idx] or is_abuse
                left_windows[note_idx] = delta
                right_windows[note_idx] = delta
            else:
                left_windows[note_idx] = min(left_windows[note_idx], delta)
                right_windows[note_idx] = max(right_windows[note_idx], delta)
        return sum(max_score), max_score

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
        if self.abuse:
            self._handle_note_abuse()
        else:
            self._handle_note_no_abuse()

    def _handle_note_no_abuse(self):
        note_time = self.note_time_stack.pop(0)
        note_delta = self.note_time_deltas.pop(0)
        note_type = self.note_type_stack.pop(0)
        note_idx = self.note_idx_stack.pop(0)
        self.combo += 1
        self.combos.append(self.combo)
        score_bonus, combo_bonus = self.evaluate_bonuses(self.special_note_types[note_idx])
        if self.fail_simulate and not self.perfect_only:
            self.judgements.append(self.evaluate_judgement(note_delta, note_type))
        else:
            self.judgements.append(Judgement.PERFECT)
        self.score_bonuses.append(score_bonus)
        self.combo_bonuses.append(combo_bonus)
        self.has_skill_change = False

    def _handle_note_abuse(self):
        note_time = self.note_time_stack.pop(0)
        note_delta = self.note_time_deltas.pop(0)
        note_type = self.note_type_stack.pop(0)
        note_idx = self.note_idx_stack.pop(0)
        special_note_types = self.special_note_types.pop(0)
        is_checkpoint = self.checkpoints.pop(0)
        is_abuse = self.is_abuse.pop(0)

        if not is_abuse:
            self.combo += 1
        self.combos.append(self.combo)

        # TODO: Sometimes abuse will heal while normal note doesn't
        score_bonus, combo_bonus = self.evaluate_bonuses(special_note_types, skip_healing=is_abuse)
        self.judgements.append(
            self.evaluate_judgement(note_delta, note_type, abuse_check=True, is_checkpoint=is_checkpoint))
        self.score_bonuses.append(score_bonus)
        self.combo_bonuses.append(combo_bonus)
        self.has_skill_change = False

    def evaluate_judgement(self, note_delta, note_type, abuse_check=False, is_checkpoint=False) -> Judgement:
        def check_cc():
            for _, skills in self.skill_queue.items():
                if isinstance(skills, Skill) and skills.is_cc:
                    return True
                for skill in skills:
                    if skill.is_cc:
                        return True
            return False

        has_cc = self.has_cc and check_cc()
        if abuse_check:
            if note_type == NoteType.TAP:
                l_g = GREAT_TAP_RANGE[self.live.difficulty]
                r_g = GREAT_TAP_RANGE[self.live.difficulty]
                l_p = PERFECT_TAP_RANGE[self.live.difficulty]
                r_p = PERFECT_TAP_RANGE[self.live.difficulty]
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

            inner_l_g = l_g
            inner_l_p = l_p if not has_cc else l_p // 2
            inner_r_p = r_p if not has_cc else r_p // 2
            inner_r_g = r_g
            if -inner_l_p <= note_delta <= inner_r_p:
                return Judgement.PERFECT
            if note_type == NoteType.TAP or note_type == NoteType.FLICK or note_type == NoteType.LONG:
                if -inner_l_g <= note_delta < -inner_l_p or inner_r_p < note_delta <= inner_r_g:
                    return Judgement.GREAT
            return Judgement.MISS
        else:
            if note_type == NoteType.TAP:
                l_p = PERFECT_TAP_RANGE[self.live.difficulty]
                r_p = PERFECT_TAP_RANGE[self.live.difficulty]
            elif note_type == NoteType.FLICK or note_type == NoteType.LONG:
                l_p = 150000
                r_p = 150000
            else:
                return Judgement.PERFECT

            if has_cc:
                l_p /= 2
                r_p /= 2
            if -l_p <= note_delta <= r_p:
                return Judgement.PERFECT
            else:
                return Judgement.GREAT

    def evaluate_bonuses(self, special_note_types, skip_healing=False):
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
        if not skip_healing:
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
            :type skill_time: encore time to check for skills before that
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

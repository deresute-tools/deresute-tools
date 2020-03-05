import time

import numpy as np

from src import customlogger as logger
from src.static.color import Color
from src.static.live_values import WEIGHT_RANGE, DIFF_MULTIPLIERS
from src.static.skill import get_sparkle_bonus


def has_skill(timestamp, upskills):
    # Faster than np.any due to early termination. Faster than iterating through elements because numpy implementation.
    for value in np.multiply(timestamp - upskills[:, 0] - 0.0001, upskills[:, 1] - timestamp):
        if value >= 0:
            return True
    return False


class Simulator:
    def __init__(self, live=None):
        self.live = live

    def _setup_simulator(self, appeals=None, support=None, extra_bonus=None):
        if extra_bonus is not None:
            assert isinstance(extra_bonus, np.ndarray) and extra_bonus.shape == (3, 3)
            self.live.set_extra_bonus(extra_bonus)
        self.notes_data = self.live.notes
        self.song_duration = self.notes_data.iloc[-1].sec
        self.note_count = len(self.notes_data)

        weight_range = np.array(WEIGHT_RANGE)
        weight_range[:, 0] = np.trunc(WEIGHT_RANGE[:, 0] / 100 * len(self.notes_data) - 1)
        for idx, (bound_l, bound_r) in enumerate(zip(weight_range[:-1, 0], weight_range[1:, 0])):
            self.notes_data.loc[int(bound_l):int(bound_r), 'weight'] = weight_range[idx][1]
        if support:
            self.support = support
        else:
            self.support = self.live.get_support()
        if appeals:
            self.total_appeal = appeals
        else:
            self.total_appeal = self.live.get_appeals() + self.support
        self.base_score = DIFF_MULTIPLIERS[self.live.level] * self.total_appeal / len(self.notes_data)

    def get_note_scores(self, skill_off=False, grouped=False):
        if not skill_off:
            bonuses_0 = (1 + self.notes_data['bonuses_0'] / 100)
            bonuses_1 = (1 + self.notes_data['bonuses_1'] / 100)
        else:
            bonuses_0 = 1
            bonuses_1 = 1
        if grouped:
            self.notes_data['note_score'] = np.round(
                self.base_score * self.notes_data['weight'] * bonuses_0 * bonuses_1)
            return self.notes_data.groupby('rep')['note_score']
        else:
            return np.round(self.base_score * self.notes_data['weight'] * bonuses_0 * bonuses_1)

    def simulate(self, times=1000, appeals=None, extra_bonus=None, support=None, perfect_play=False):
        start = time.time()
        logger.debug("Unit: {}".format(self.live.unit))
        logger.debug("Song: {} - {}".format(self.live.music_name, self.live.difficulty))
        if perfect_play:
            times = 1
            logger.debug("Only need 1 simulation for perfect play.")
        if times == 1:
            perfect_play = True
        res = self._simulate(times, appeals=appeals, extra_bonus=extra_bonus, support=support,
                             perfect_play=perfect_play)
        logger.debug("Total run time for {} trials: {:04.2f}s".format(times, time.time() - start))
        return res

    def _simulate(self,
                  times=1000,
                  appeals=None,
                  extra_bonus=None,
                  support=None,
                  perfect_play=False):

        self._setup_simulator(appeals=appeals, support=support, extra_bonus=extra_bonus)
        grand = self.live.is_grand

        self._simulate_internal(times=times, grand=grand, time_offset=0, fail_simulate=False)
        perfect_score = self.get_note_scores().sum()
        skill_off = self.get_note_scores(skill_off=True).sum()

        if perfect_play:
            base = perfect_score
            deltas = np.zeros(1)
        else:
            self._simulate_internal(times=times, grand=grand, time_offset=0, fail_simulate=True)
            grouped_note_scores = self.get_note_scores(grouped=True)
            totals = grouped_note_scores.sum()
            base = totals.mean()
            deltas = totals - base

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
        return self.total_appeal, perfect_score, skill_off, base, deltas

    def _simulate_internal(self, grand, times, fail_simulate=False, time_offset=0.0):
        results = self._helper_initialize_skill_activations(times=times, grand=grand,
                                                            time_offset=time_offset,
                                                            fail_simulate=fail_simulate)
        self.has_sparkle, self.has_support, self.has_alternate = results

        np_v, np_b = self._helper_initialize_skill_bonuses(grand=grand, sparkle=False, alternate=self.has_alternate)
        self._helper_evaluate_skill_bonuses(np_v, np_b, grand=grand)

        if self.has_sparkle:
            np_v, np_b = self._helper_initialize_skill_bonuses(grand=grand, sparkle=self.has_sparkle,
                                                               alternate=not self.has_alternate)
            self._helper_evaluate_skill_bonuses(np_v, np_b, grand=grand)

    def _helper_evaluate_skill_bonuses(self, np_v, np_b, grand, mutate_df=True):
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
        np_v[:, :2, :, :][np_v[:, :2, :, :] != 0] = np.clip(np_v[:, :2, :, :][np_v[:, :2, :, :] != 0] - 100,
                                                            a_min=-5000, a_max=5000)
        np_b[:, :3, :, :][np_b[:, :3, :, :] != 0] = np.clip(np_b[:, :3, :, :][np_b[:, :3, :, :] != 0] - 1000,
                                                            a_min=-9000, a_max=9000)
        # Pre-calculate total/max boosts to reduce redundant computations
        np_b_sum = np_b.sum(axis=3)
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

            for card_idx in range(unit_idx * 5, (unit_idx + 1) * 5):
                skill = unit.get_card(card_idx % 5).skill
                if skill.is_alternate:
                    alternate_mask = np_v[:, 1, :, card_idx] < 0
                    original_value = np_v[:, 1, :, card_idx][alternate_mask]
                np_v[:, :3, :, card_idx] = np.ceil(np_v[:, :3, :, card_idx] * (1 + boost_array[:, :3] / 1000))
                if skill.is_alternate:
                    np_v[:, 1, :, card_idx][alternate_mask] = original_value
                if skill.is_support:
                    mask = np_v[:, 3, :, card_idx] == 0
                    np_v[:, 3, :, card_idx] += boost_array[:, 3]
                    np_v[:, 3, :, card_idx][mask] = 0
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
                    min_tensor = np_vu[:, :, unit_idx].min(axis=2)
                    mask = np.logical_and(skill_bonuses[:, :, unit_idx] == 0, min_tensor < 0)
                    skill_bonuses[:, :, unit_idx][mask] = min_tensor[mask]
        # Unify effects across units
        skill_bonuses_final = skill_bonuses.max(axis=2)
        if self.has_alternate:
            min_tensor = skill_bonuses.min(axis=2)
            mask = np.logical_and(skill_bonuses_final == 0, min_tensor < 0)
            skill_bonuses_final[mask] = min_tensor[mask]
        if mutate_df:
            # Fill values into DataFrame
            value_range = 4 if self.has_support else 3
            for _ in range(value_range):
                self.notes_data["bonuses_{}".format(_)] = skill_bonuses_final[:, _]
            # Evaluate HP
            self.notes_data['life'] = np.clip(
                self.live.get_life()
                + self.notes_data['bonuses_2'].groupby(self.notes_data.index // self.note_count).cumsum(),
                a_min=0, a_max=2 * self.live.get_life())
        return skill_bonuses_final

    def _helper_initialize_skill_bonuses(self, grand, np_v=None, np_b=None, sparkle=False, alternate=False):
        """
        Initializes skill values in DataFrame.
        :param grand: True if GRAND LIVE, else False.
        :param sparkle: True if there is at least one LS in the unit. Will replace LS value with the correct values according to HP.
        :return: 2-tuple of numpy arrays containing skill values (no boost) and boost values. Both arrays are of shape Notes x Values x Colors x Cards
        """

        def handle_boost(skill):
            if not skill.color_target:
                targets = [_.value for _ in [Color.CUTE, Color.COOL, Color.PASSION]]
            else:
                targets = [skill.color.value]
            for _, __ in enumerate(skill.values):
                np_b[:, _, targets, unit_idx * 5 + card_idx] = __

        def handle_act(skill):
            np_v[self.notes_data[self.notes_data['note_type'] == skill.act].index,
                 0, skill.color.value, unit_idx * 5 + card_idx] = skill.v1
            np_v[self.notes_data[self.notes_data['note_type'] != skill.act].index,
                 0, skill.color.value, unit_idx * 5 + card_idx] = skill.v0

        def handle_sparkle(skill):
            trimmed_life = (self.notes_data['life'] // 10).astype(int)
            np_v[:, 0, skill.color.value, unit_idx * 5 + card_idx] = 0
            np_v[:, 1, skill.color.value, unit_idx * 5 + card_idx] = trimmed_life.map(
                get_sparkle_bonus(rarity=card.rarity, grand=grand))

        def handle_alternate(alternates):
            non_alternate = list(set(range(units * 5)).difference(set(alternates)))
            alternate_value = np.ceil(np.clip(np_v[:, 0:1, :, non_alternate] - 100, a_min=0, a_max=9000) * 1.5)
            alternate_value[alternate_value != 0] += 100
            alternate_value = np.maximum.accumulate(alternate_value.max(axis=2).max(axis=2), axis=0)[:, 0]
            first_score_note = np.argwhere(alternate_value > 0)[0][0]
            first_score_note = self.notes_data.iloc[first_score_note].sec
            for skill_idx in alternates:
                skill = self.live.unit.get_card(skill_idx).skill
                fail_alternate_notes = self.notes_data[self.notes_data.sec < first_score_note][
                    "skill_{}_l".format(skill_idx)].max()
                if not np.isnan(fail_alternate_notes):
                    remove_index = self.notes_data[
                        self.notes_data["skill_{}_l".format(skill_idx)] <= fail_alternate_notes].index.max()
                    # Negate where skill not activated
                    np_v[:remove_index + 1, 0:2, skill.color.value, skill_idx] = 0
                np_v[:, 0, skill.color.value, skill_idx] = np_v[:, 0, skill.color.value, skill_idx] * alternate_value

        def null_deactivated_skills():
            card_range = range(unit_idx * 5, (unit_idx + 1) * 5)
            value_range = 4 if self.has_support else 3
            for i in range(value_range):
                for j in range(3):
                    np_v[:, i, j, card_range] = \
                        np_v[:, i, j, card_range] \
                        * self.notes_data[['skill_{}'.format(unit_idx * 5 + _) for _ in range(5)]]
                    np_b[:, i, j, card_range] = \
                        np_b[:, i, j, card_range] \
                        * self.notes_data[['skill_{}'.format(unit_idx * 5 + _) for _ in range(5)]]

        units = 3 if grand else 1
        np_v = np.zeros((len(self.notes_data), 4, 3, 5 * units))  # Notes x Values x Colors x Cards
        np_b = np.zeros((len(self.notes_data), 4, 3, 5 * units))  # Notes x Values x Colors x Cards
        alternates = list()
        for unit_idx, unit in enumerate(self.live.unit.all_units):
            unit.convert_motif(grand=grand)
            for card_idx, card in enumerate(unit.all_cards()):
                skill = card.skill
                if skill.boost:
                    handle_boost(skill)
                else:
                    if skill.act:
                        handle_act(skill)
                        continue
                    if skill.skill_type == 25 and sparkle:
                        handle_sparkle(skill)
                        continue
                    elif skill.skill_type == 39 and alternate:
                        alternates.append(unit_idx * 5 + card_idx)
                    for _, __ in enumerate(skill.values):
                        np_v[:, _, skill.color.value, unit_idx * 5 + card_idx] = __
            null_deactivated_skills()
        if alternate:
            handle_alternate(alternates)
        return np_v, np_b

    def _helper_initialize_skill_activations(self, grand, times, time_offset=0.0, fail_simulate=False):
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

        if fail_simulate:
            logger.debug("Simulating fail play")
            self.notes_data = self.notes_data.append([self.notes_data] * (times - 1), ignore_index=True)
            self.notes_data['rep'] = np.repeat(np.arange(times), self.note_count)

        for unit_idx, unit in enumerate(self.live.unit.all_units):
            for card_idx, card in enumerate(unit.all_cards()):
                skill = card.skill
                if skill.skill_type == 25:
                    has_sparkle = True
                elif skill.skill_type == 39:
                    has_alternate = True
                if skill.v3 > 0 and not skill.boost:
                    # Use for early termination
                    has_support = True
        for unit_idx, unit in enumerate(self.live.unit.all_units):
            for card_idx, card in enumerate(unit.all_cards()):
                skill = card.skill
                probability = self.live.get_probability(unit_idx * 5 + card_idx)
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
                        self.notes_data.loc[(note_times > left) & (note_times <= right),
                                            'skill_{}'.format(unit_idx * 5 + card_idx)] = 1
                        if has_alternate:
                            self.notes_data.loc[(note_times > left) & (note_times < right),
                                                'skill_{}_l'.format(unit_idx * 5 + card_idx)] = left
                            self.notes_data.loc[(note_times > left) & (note_times <= right),
                                                'skill_{}_r'.format(unit_idx * 5 + card_idx)] = right
                else:
                    note_times = self.notes_data.sec + np.random.random(len(self.notes_data)) * 0.06 - 0.03
                    self.notes_data['skill_{}'.format(unit_idx * 5 + card_idx)] = 0
                    for skill_activation, skill_range in enumerate(skills):
                        left, right = skill_range
                        if probability < 1:
                            rep_rolls = np.random.choice(2, times, p=[1 - probability, probability])
                            rep_rolls = rep_rolls * np.arange(1, 1 + times) - 1
                            rep_rolls = rep_rolls[rep_rolls != -1]
                            self.notes_data.loc[(note_times > left) & (note_times <= right)
                                                & (self.notes_data.rep.isin(rep_rolls)),
                                                'skill_{}'.format(unit_idx * 5 + card_idx)] = 1
                        else:
                            # Save a bit more time
                            self.notes_data.loc[(note_times > left) & (note_times <= right),
                                                'skill_{}'.format(unit_idx * 5 + card_idx)] = 1
        return has_sparkle, has_support, has_alternate

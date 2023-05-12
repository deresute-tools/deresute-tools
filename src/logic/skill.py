import numpy as np
import pyximport

from db import db
from static.color import Color
from static.note_type import NoteType
from static.skill import SKILL_BASE

pyximport.install(language_level=3)
BOOST_TYPES = {20, 32, 33, 34, 38}
COLOR_TARGETS = {21, 22, 23, 32, 33, 34}
ACT_TYPES = {28: NoteType.LONG, 29: NoteType.FLICK, 30: NoteType.SLIDE}
SUPPORT_TYPES = {5, 6, 7}
COMBO_SUPPORT_TYPES = {9, 14}
COMMON_TIMERS = [(7, 4.5, 'h'), (9, 6, 'h'), (11, 7.5, 'h'), (12, 7.5, 'm'),
                 (6, 4.5, 'm'), (9, 7.5, 'm'), (11, 9, 'm'), (13, 9, 'h')]


class Skill:
    def __init__(self, color=Color.CUTE, duration=0, probability=0, interval=999,
                 values=None, v0=0, v1=0, v2=0, v3=0, offset=0,
                 boost=False, color_target=False, act=None, bonus_skill=2000, skill_type=None,
                 min_requirements=None, max_requirements=None, life_requirement=0):
        if values is None and v0 == v1 == v2 == v3 == 0:
            raise ValueError("Invalid skill values", values, v0, v1, v2, v3)

        if min_requirements is not None:
            assert len(min_requirements) == 3
        else:
            min_requirements = np.array([0, 0, 0])

        if max_requirements is not None:
            assert len(max_requirements) == 3
        else:
            max_requirements = np.array([99, 99, 99])

        self.color = color
        self.duration = duration
        self.probability = probability + bonus_skill
        self.cached_probability = self.probability
        self.max_probability = probability
        self.interval = interval
        self.v0, self.v1, self.v2, self.v3 = tuple(values)
        self.values = [self.v0, self.v1, self.v2, self.v3]
        self.offset = offset
        self.boost = boost
        self.color_target = color_target
        self.act = act
        self.skill_type = skill_type
        self.min_requirements = min_requirements
        self.max_requirements = max_requirements
        self.life_requirement = life_requirement
        self.targets = self._generate_targets()
        self.normalized = False
        self.original_unit_idx = None

    def set_original_unit_idx(self, idx):
        self.original_unit_idx = idx

    def _generate_targets(self):
        if self.skill_type == 21 or self.skill_type == 32:
            return [0]
        if self.skill_type == 22 or self.skill_type == 33:
            return [1]
        if self.skill_type == 23 or self.skill_type == 34:
            return [2]
        return [0, 1, 2]

    @property
    def is_support(self):
        return self.skill_type in SUPPORT_TYPES

    @property
    def is_guard(self):
        return self.skill_type == 12

    @property
    def is_overload(self):
        return self.skill_type == 14

    @property
    def is_cc(self):
        return self.skill_type == 15

    @property
    def is_encore(self):
        return self.skill_type == 16

    @property
    def is_focus(self):
        return 21 <= self.skill_type <= 23

    @property
    def is_sparkle(self):
        return self.skill_type == 25

    @property
    def is_tuning(self):
        return self.skill_type == 31

    @property
    def is_motif(self):
        return 35 <= self.skill_type <= 37

    @property
    def is_alternate(self):
        return self.skill_type == 39

    @property
    def is_refrain(self):
        return self.skill_type == 40

    @property
    def is_magic(self):
        return self.skill_type == 41

    @property
    def is_mutual(self):
        return self.skill_type == 42

    @property
    def is_overdrive(self):
        return self.skill_type == 43

    @classmethod
    def _fetch_skill_data_from_db(cls, skill_id):
        return db.masterdb.execute_and_fetchone(
            """
            SELECT skill_data.*,
                card_data.attribute,
                probability_type.probability_max,
                available_time_type.available_time_max
            FROM card_data, skill_data, probability_type, available_time_type
            WHERE skill_data.id = ? AND 
                card_data.skill_id = ? AND 
                probability_type.probability_type = skill_data.probability_type AND
                available_time_type.available_time_type = skill_data.available_time_type
            """,
            params=[skill_id, skill_id],
            out_dict=True)

    @classmethod
    def _fetch_boost_value_from_db(cls, skill_value):
        values = db.masterdb.execute_and_fetchone(
            """
            SELECT  sbt1.boost_value_1 as v0, 
                    sbt1.boost_value_2 as v1,
                    sbt1.boost_value_3 as v2,
                    sbt2.boost_value_2 as v3
            FROM    skill_boost_type as sbt1,
                    skill_boost_type as sbt2
            WHERE   sbt1.skill_value = ? 
            AND     sbt1.target_type = 26
            AND     sbt2.skill_value = ? 
            AND     sbt2.target_type = 31
            """,
            params=[skill_value, skill_value],
            out_dict=True)
        values = [values["v{}".format(_)] for _ in range(4)]
        return values

    @classmethod
    def _handle_skill_type(cls, skill_type, skill_values):
        assert len(skill_values) == 3
        values = [0, 0, 0, 0]
        if skill_type in SUPPORT_TYPES:
            values[3] = skill_type - 4
        elif skill_type == 4:  # CU
            values[1] = skill_values[0]
        elif skill_type == 31:  # Tuning
            values[1] = skill_values[0]
            values[3] = 2
        elif (skill_type == 24  # All-round
                or skill_type == 43):  # Overdrive
            values[1] = skill_values[0]
            values[2] = skill_values[1]
        elif skill_type == 17:  # Healer
            values[2] = skill_values[0]
        else:
            values = [skill_values[0], skill_values[1], skill_values[2], 0]
        return values

    @classmethod
    def from_id(cls, skill_id, bonus_skill=2000):
        if skill_id == 0:
            return cls(values=[0, 0, 0, 0])  # Default skill that has 0 duration
        skill_data = cls._fetch_skill_data_from_db(skill_id)

        min_requirements, max_requirements = None, None
        if skill_data['skill_trigger_type'] == 2:
            min_requirements = np.array([0, 0, 0])
            max_requirements = np.array([0, 0, 0])
            max_requirements[skill_data['skill_trigger_value'] - 1] = 99
        elif skill_data['skill_trigger_type'] == 3:
            min_requirements = [1, 1, 1]

        life_requirement = skill_data['skill_trigger_value'] if skill_data['skill_type'] == 14 else 0

        is_boost = skill_data['skill_type'] in BOOST_TYPES
        if is_boost:
            values = cls._fetch_boost_value_from_db(skill_data['value'])
        else:
            values = cls._handle_skill_type(skill_data['skill_type'],
                                            (skill_data['value'], skill_data['value_2'], skill_data['value_3']))
        return cls(
            color=Color(skill_data['attribute'] - 1),  # CU=1 CO=2 PA=3,
            duration=skill_data['available_time_max'] / 100,
            probability=skill_data['probability_max'],
            interval=skill_data['condition'],
            values=values,
            offset=0,
            boost=is_boost,
            color_target=skill_data['skill_type'] in COLOR_TARGETS,
            act=ACT_TYPES[skill_data['skill_type']] if skill_data['skill_type'] in ACT_TYPES else None,
            bonus_skill=bonus_skill,
            skill_type=skill_data['skill_type'],
            min_requirements=min_requirements,
            max_requirements=max_requirements,
            life_requirement=life_requirement
        )

    def __eq__(self, other):
        if other is None or not isinstance(other, Skill):
            return False
        return self.skill_type == other.skill_type and self.duration == other.duration and self.interval == other.interval

    def __str__(self):
        try:
            return "{} {}/{}: {} {} {} {}".format(SKILL_BASE[self.skill_type]["name"], self.duration, self.interval,
                                                  self.v0, self.v1, self.v2, self.v3)
        except:
            return None

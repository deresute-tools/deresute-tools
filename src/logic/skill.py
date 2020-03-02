from src.db import db
from src.static.color import Color
from src.static.note_type import NoteType

BOOST_TYPES = {20, 32, 33, 34, 38}
COLOR_TARGETS = {21, 22, 23, 32, 33, 34}
ACT_TYPES = {28: NoteType.LONG, 29: NoteType.FLICK, 30: NoteType.SLIDE}
SUPPORT_TYPES = {5, 6, 7}
COMBO_SUPPORT_TYPES = {9, 14}


class Skill:
    def __init__(self, color=Color.CUTE, duration=0, probability=0, interval=999,
                 values=None, v0=0, v1=0, v2=0, v3=0, offset=0,
                 boost=False, color_target=False, act=None, bonus_skill=2000, skill_type=None):
        if values is None and v0 == v1 == v2 == v3 == 0:
            raise ValueError("Invalid skill values", values, v0, v1, v2, v3)

        self.color = color
        self.duration = duration
        self.probability = probability + bonus_skill
        self.interval = interval
        self.v0, self.v1, self.v2, self.v3 = tuple(values)
        self.offset = offset
        self.boost = boost
        self.color_target = color_target
        self.act = act
        self.skill_type = skill_type

    @property
    def values(self):
        return [self.v0, self.v1, self.v2, self.v3]

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
            values[3] = skill_values[1]
        elif skill_type == 24:  # All-round
            values[0] = skill_values[0]
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
            skill_type=skill_data['skill_type']
        )

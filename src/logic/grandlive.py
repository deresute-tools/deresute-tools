import numpy as np

from src.logic.grandunit import GrandUnit
from src.logic.live import BaseLive, Live
from src.static.color import Color


class GrandLive(BaseLive):
    unit: GrandUnit

    def __init__(self, music_name=None, difficulty=None, unit=None):
        self.unit_lives = list()
        for i in range(3):
            dummy_live = Live()
            self.unit_lives.append(dummy_live)
        super().__init__(music_name, difficulty, unit)

    def initialize_music(self, music_name=None, difficulty=None, unit=None):
        super().initialize_music(music_name, difficulty, unit)
        for i in range(3):
            self.unit_lives[i].initialize_music(music_name, difficulty, unit)

    def set_music(self, music_name=None, score_id=None, difficulty=None, event=None):
        super().set_music(music_name, score_id, difficulty, event)
        for i in range(3):
            self.unit_lives[i].set_music(music_name, score_id, difficulty, event)

    def set_chara_bonus(self, chara_bonus_set, chara_bonus_value):
        super().set_chara_bonus(chara_bonus_set, chara_bonus_value)
        for i in range(3):
            self.unit_lives[i].set_chara_bonus(chara_bonus_set, chara_bonus_value)

    def reset_attributes(self, hard_reset=True):
        for i in range(3):
            self.unit_lives[i].reset_attributes(hard_reset)

    def set_unit(self, unit):
        assert isinstance(unit, GrandUnit)
        self.unit = unit
        for i in range(3):
            self.unit_lives[i].set_unit(self.unit.get_unit(i))
            self.unit_lives[i].reset_attributes()

    def set_extra_bonus(self, bonuses, special_option, special_value):
        super().set_extra_bonus(bonuses, special_option, special_value)
        for i in range(3):
            self.unit_lives[i].set_extra_bonus(bonuses, special_option, special_value)

    def get_attributes(self):
        self.attribute_cache_check()
        if self.attributes is not None:
            return self.attributes

        if self.attributes is not None:
            return self.attributes

        self.get_bonuses()
        attributes = np.zeros((4, 3))  # Attributes x Units
        for unit_idx in range(3):
            attributes[:, unit_idx] = self.unit_lives[unit_idx].get_attributes()
        self.attributes = attributes
        return self.attributes

    def get_life(self):
        return np.ceil(self.get_attributes()[3].mean())

    @property
    def is_grand(self):
        return True

    def get_bonuses(self):
        for unit_live in self.unit_lives:
            unit_live.get_bonuses()

    def get_probability(self, idx=None):
        return self.unit_lives[idx // 5].get_probability(idx % 5)

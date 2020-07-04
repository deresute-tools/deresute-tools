import numpy as np

from src.logic.grandunit import GrandUnit
from src.logic.live import Live
from src.static.color import Color


class GrandLive(Live):
    unit: GrandUnit

    def set_unit(self, unit):
        assert isinstance(unit, GrandUnit)
        self.unit = unit

    def get_attributes(self):
        if self.attributes is not None:
            return self.attributes
        attributes = np.zeros((4, 3))  # Attributes x Units
        for unit_idx, unit in enumerate(self.unit.all_units):
            bonuses = unit.leader_bonuses(song_color=self.color)[:4, :]
            bonuses[:3] += 10  # Furniture
            if self.color == Color.ALL:
                bonuses[:3] += 30
            else:
                bonuses[:3, self.color] += 30
            character_specific_bonuses = np.zeros((5, 4, 3))
            for i in range(5):
                character_specific_bonuses[i, :, :] = bonuses
                if unit.get_card(i).chara_id in self.chara_bonus_set:
                    character_specific_bonuses[i, :3, :] += self.chara_bonus_value
            bonuses = 1 + character_specific_bonuses / 100

            attributes[:, unit_idx] = np.ceil(np.multiply(unit.base_attributes, bonuses)).sum(axis=0).sum(axis=1)
        self.attributes = attributes
        return self.attributes

    def get_life(self):
        return np.ceil(self.get_attributes()[3].mean())

    @property
    def is_grand(self):
        return True

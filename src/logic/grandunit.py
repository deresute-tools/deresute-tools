from src.logic.unit import Unit


class GrandUnit:
    ua: Unit
    ub: Unit
    uc: Unit

    def __init__(self, ua, ub, uc):
        self.ua = ua
        self.ub = ub
        self.uc = uc
        self._units = [self.ua, self.ub, self.uc]
        for idx, unit in enumerate(self._units):
            unit.set_offset(idx)

    @classmethod
    def from_list(cls, card_list):
        return cls(*card_list)

    def get_unit(self, idx):
        return self._units[idx]

    @property
    def all_units(self):
        return self._units

    def all_cards(self):
        result = []
        for unit in self._units:
            result.extend(unit.all_cards())
        return result

    def get_card(self, idx):
        return self.all_cards()[idx]

    def __str__(self):
        return " ".join(map(str, self._units))

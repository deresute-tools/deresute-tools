from abc import ABC, abstractmethod

import numpy as np

from src.db import db
from src.exceptions import InvalidUnit
from src.logic.card import Card
from src.logic.search import card_query


class BaseUnit(ABC):
    @classmethod
    @abstractmethod
    def from_list(cls, cards, custom_pots=None):
        pass

    @abstractmethod
    def all_units(self):
        pass

    @abstractmethod
    def all_cards(self):
        pass

    @abstractmethod
    def get_card(self, idx):
        pass


class Unit(BaseUnit):
    def __init__(self, c0, c1, c2, c3, c4, cg=None, resonance=None):
        for _ in [c0, c1, c2, c3, c4]:
            if not isinstance(_, Card):
                raise InvalidUnit("{} is not a card".format(_))
        if cg is None:
            self._cards = [c0, c1, c2, c3, c4]
        else:
            self._cards = [c0, c1, c2, c3, c4, cg]
        if resonance is not None and isinstance(resonance, bool):
            self.resonance = resonance
        else:
            self.resonance = self._resonance_check()
        self._skill_check()

    @classmethod
    def from_query(cls, query, custom_pots=None):
        card_ids = card_query.convert_short_name_to_id(query)
        if len(card_ids) < 5 or len(card_ids) > 6:
            raise ValueError("Invalid number of cards in query: {}".format(query))
        return cls.from_list(card_ids, custom_pots)

    @classmethod
    def from_list(cls, cards, custom_pots=None):
        if len(cards) < 5 or len(cards) > 6:
            raise InvalidUnit("Invalid number of cards: {}".format(cards))
        results = list()
        for c_idx, card in enumerate(cards):
            if isinstance(card, str):
                card = int(card)
            if isinstance(card, int):
                card = Card.from_id(card, custom_pots)
            if card is not None:
                assert isinstance(card, Card)
            if card is not None and custom_pots is not None:
                card.vo_pots = custom_pots[0]
                card.vi_pots = custom_pots[1]
                card.da_pots = custom_pots[2]
                card.li_pots = custom_pots[3]
                card.sk_pots = custom_pots[4]
                card.refresh_values()
            results.append(card)
        return cls(*results)

    def get_card(self, idx):
        return self._cards[idx]

    def all_cards(self, guest=False):
        if guest and len(self._cards) == 6:
            return self._cards
        else:
            return self._cards[:5]

    def set_offset(self, offset):
        for card in filter(lambda x: x is not None, self._cards):
            card.set_skill_offset(offset)

    def leader_bonuses(self, song_color=None):
        colors = np.zeros(3)
        skills = set()
        for card in self._cards:
            if card is None:
                continue
            colors[card.color.value] += 1
            skills.add(card.skill.skill_type)

        bonuses = np.zeros((5, 3))  # Attributes x Colors
        if len(self._cards) == 6:
            leaders_to_include = [self._cards[0], self._cards[-1]]
        else:
            leaders_to_include = [self._cards[0]]
        is_blessed = any(map(lambda _: _.leader.bless, leaders_to_include))

        if is_blessed:
            agg_func = np.maximum
            leaders_to_include = self._cards.copy()
        else:
            agg_func = np.add

        # Separate into two lists, non reso and reso
        resos = [card for card in leaders_to_include if card.leader.resonance]
        for card in resos:
            leaders_to_include.remove(card)

        for card in leaders_to_include:
            if card is None:
                continue
            if np.greater_equal(colors, card.leader.min_requirements).all() \
                    and np.less_equal(colors, card.leader.max_requirements).all():
                bonuses_to_add = card.leader.bonuses
                # Unison and correct song color
                if card.leader.unison and song_color == card.color:
                    bonuses_to_add = card.leader.song_bonuses
                bonuses = agg_func(bonuses, bonuses_to_add)

        reso_mask = np.zeros((5,3))
        for card in resos:
            # Does not satisfy the resonance constraint
            if not self.resonance:
                continue
            reso_mask += card.leader.bonuses
        reso_mask = np.clip(reso_mask, a_min=-100, a_max=5000)
        bonuses += reso_mask
        bonuses = np.clip(bonuses, a_min=-100, a_max=5000)
        return bonuses

    def _skill_check(self):
        colors = np.zeros(3)
        for card in self._cards:
            if card is None:
                continue
            colors[card.color.value] += 1

        for card in self.all_cards(guest=False):
            if card is None:
                continue
            card.skill.probability = card.skill.cached_probability
            if np.greater_equal(colors, card.skill.min_requirements).all() \
                    and np.less_equal(colors, card.skill.max_requirements).all():
                continue
            card.skill.probability = 0

    def _resonance_check(self):
        skills = {_card.skill.skill_type for _card in self._cards if _card is not None}
        if len(self._cards) == 6:
            cards_to_test = [self._cards[0], self._cards[-1]]
        else:
            cards_to_test = [self._cards[0]]
        for card in cards_to_test:
            if card is None:
                continue
            if card.leader.bless:
                cards_to_test = self._cards
                break
        for card in cards_to_test:
            if card is None:
                continue
            if card.leader.resonance:
                if len(skills) < 5:
                    continue
                return True
        return False

    def convert_motif(self, grand=False):
        for card in self._cards[:5]:
            if card.skill.skill_type == 35:
                total = self._get_motif_vocal()
            elif card.skill.skill_type == 36:
                total = self._get_motif_dance()
            elif card.skill.skill_type == 37:
                total = self._get_motif_visual()
            else:
                continue
            if grand:
                values = [_[0] for _ in
                          db.masterdb.execute_and_fetchall("SELECT type_01_value FROM skill_motif_value_grand")]
            else:
                values = [_[0] for _ in db.masterdb.execute_and_fetchall("SELECT type_01_value FROM skill_motif_value")]
            total = total // 1000
            if total >= len(values):
                total = len(values) - 1
            card.skill.v0 = values[int(total)]

    def update_card(self, idx, card):
        self._cards[idx] = card

    def _get_motif_vocal(self):
        return sum(card.vocal for card in self._cards[:5])

    def _get_motif_dance(self):
        return sum(card.dance for card in self._cards[:5])

    def _get_motif_visual(self):
        return sum(card.visual for card in self._cards[:5])

    def print_skills(self):
        print([card.skill.skill_type for card in self._cards])

    @property
    def base_attributes(self):
        attributes = np.zeros((len(self._cards), 4, 3))  # Cards x Attributes x Colors
        for idx, card in enumerate(self._cards):
            attributes[idx, 0, card.color.value] += card.vocal
            attributes[idx, 1, card.color.value] += card.visual
            attributes[idx, 2, card.color.value] += card.dance
            attributes[idx, 3, card.color.value] += card.life
        return attributes

    @property
    def all_units(self):
        return [self]

    def __str__(self):
        ids = [card.card_id for card in self._cards]
        return " ".join(card_query.convert_id_to_short_name(ids))

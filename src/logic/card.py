from src.db import db
from src.logic.leader import Leader
from src.logic.skill import Skill
from src.logic.search import card_query
from src.static.color import Color


class Card:
    def __init__(self, vo, da, vi, li, sk, le, color, ra=8, card_id=None):
        assert isinstance(sk, Skill)
        assert isinstance(le, Leader)
        self.vo = vo
        self.vi = vi
        self.da = da
        self.li = li
        self.sk = sk
        self.le = le
        self.color = color
        self.ra = ra
        self.card_id = card_id

    @classmethod
    def from_query(cls, query, *args, **kwargs):
        card_id = card_query.convert_short_name_to_id(query)
        if len(card_id) != 1:
            raise ValueError("Not 1 card in query: {}".format(query))
        return cls.from_id(card_id[0], *args, **kwargs)

    @classmethod
    def from_id(cls, card_id, custom_pots=None):
        if custom_pots:
            assert len(custom_pots) == 5
            database = (db.masterdb, "card_data")
        else:
            database = (db.cachedb, "card_data_cache")

        card_data = database[0].execute_and_fetchone(
            """
            SELECT * FROM {} WHERE id = ?
            """.format(database[1]),
            params=[card_id],
            out_dict=True)

        bonuses = [card_data['bonus_vocal'], card_data['bonus_visual'], card_data['bonus_dance'],
                   card_data['bonus_hp'], 0]
        if custom_pots:
            rarity = card_data['rarity'] if card_data['rarity'] % 2 == 1 else card_data['rarity'] - 1
            attributes = ['vo', 'vi', 'da', 'li', 'sk']
            for idx, key in enumerate(attributes):
                if custom_pots[idx] == 0:
                    continue
                bonuses[idx] += db.masterdb.execute_and_fetchone("""
                        SELECT value_rare_{} FROM potential_value_{} WHERE potential_level = ?
                    """.format(rarity, key), [custom_pots[idx]])[0]
        else:
            bonuses[-1] = card_data['bonus_skill']

        return cls(vo=card_data['vocal_max'] + bonuses[0],
                   vi=card_data['visual_max'] + bonuses[1],
                   da=card_data['dance_max'] + bonuses[2],
                   li=card_data['hp_max'] + bonuses[3],
                   ra=card_data['rarity'],
                   sk=Skill.from_id(card_data['skill_id'], bonuses[4]),
                   le=Leader.from_id(card_data['leader_skill_id']),
                   color=Color(card_data['attribute'] - 1),
                   card_id=card_id)

    @property
    def vocal(self):
        return self.vo

    @property
    def dance(self):
        return self.da

    @property
    def visual(self):
        return self.vi

    @property
    def life(self):
        return self.li

    @property
    def rarity(self):
        return self.ra

    @property
    def skill(self):
        return self.sk

    @property
    def center(self):
        return self.le

    @property
    def leader(self):
        return self.le

    @property
    def total(self):
        return self.vo + self.da + self.vi

    def set_skill_offset(self, offset):
        self.sk.offset = offset

    def __str__(self):
        short_name = db.cachedb.execute_and_fetchone("SELECT card_short_name FROM card_name_cache WHERE card_id = ?",
                                                     [self.card_id])
        return short_name[0]

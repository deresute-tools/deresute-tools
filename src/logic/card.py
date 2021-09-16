from db import db
from logic.leader import Leader
from logic.search import card_query
from logic.skill import Skill
from static.color import Color


class Card:
    def __init__(self, vo, da, vi, li, sk, le, color, ra=8, card_id=None, chara_id=None,
                 vo_pots=0, vi_pots=0, da_pots=0, li_pots=0, sk_pots=0, star=1,
                 base_vo=0, base_da=0, base_vi=0, base_li=0):
        assert isinstance(sk, Skill)
        assert isinstance(le, Leader)
        self.vo = vo
        self.vi = vi
        self.da = da
        self.li = li
        self.base_vo = base_vo
        self.base_da = base_da
        self.base_vi = base_vi
        self.base_li = base_li
        self.sk = sk
        self.le = le
        self.vo_pots = vo_pots
        self.vi_pots = vi_pots
        self.da_pots = da_pots
        self.li_pots = li_pots
        self.sk_pots = sk_pots
        self.star = star
        self.color = color
        self.ra = ra
        self.card_id = card_id
        self.chara_id = chara_id
        self.is_refreshed = True

    @classmethod
    def from_query(cls, query, *args, **kwargs):
        card_id = card_query.convert_short_name_to_id(query)
        if len(card_id) != 1:
            raise ValueError("Not 1 card in query: {}".format(query))
        return cls.from_id(card_id[0], *args, **kwargs)

    @classmethod
    def from_id(cls, card_id, custom_pots=None):
        if card_id is None:
            return None
        if custom_pots:
            assert len(custom_pots) == 5
        card_data = db.masterdb.execute_and_fetchone(
            """
            SELECT * FROM {} WHERE id = ?
            """.format("card_data"),
            params=[card_id],
            out_dict=True)

        bonuses = [card_data['bonus_vocal'], card_data['bonus_visual'], card_data['bonus_dance'],
                   card_data['bonus_hp'], 0]

        if custom_pots:
            potentials = custom_pots
        else:
            potentials = \
                db.cachedb.execute_and_fetchall("SELECT vo,vi,da,li,sk FROM potential_cache WHERE chara_id = ?",
                                                params=[card_data['chara_id']])[0]

        rarity = card_data['rarity'] if card_data['rarity'] % 2 == 1 else card_data['rarity'] - 1
        attributes = ['vo', 'vi', 'da', 'li', 'sk']
        for idx, key in enumerate(attributes):
            if potentials[idx] == 0:
                continue
            bonuses[idx] += db.masterdb.execute_and_fetchone("""
                    SELECT value_rare_{} FROM potential_value_{} WHERE potential_level = ?
                """.format(rarity, key), [potentials[idx]])[0]

        owned = db.cachedb.execute_and_fetchall("""
                            SELECT number FROM owned_card WHERE card_id = ?
                        """, [card_id])[0][0]
        if owned == 0:
            owned = 1

        return cls(vo=card_data['vocal_max'] + bonuses[0],
                   vi=card_data['visual_max'] + bonuses[1],
                   da=card_data['dance_max'] + bonuses[2],
                   li=card_data['hp_max'] + bonuses[3],
                   base_vo=card_data['vocal_max'],
                   base_vi=card_data['visual_max'],
                   base_da=card_data['dance_max'],
                   base_li=card_data['hp_max'],
                   ra=card_data['rarity'],
                   vo_pots=potentials[0],
                   vi_pots=potentials[1],
                   da_pots=potentials[2],
                   li_pots=potentials[3],
                   sk_pots=potentials[4],
                   star=owned,
                   sk=Skill.from_id(card_data['skill_id'], bonuses[4]),
                   le=Leader.from_id(card_data['leader_skill_id']),
                   color=Color(card_data['attribute'] - 1),
                   card_id=card_id,
                   chara_id=card_data['chara_id'])

    def clone_card(self):
        clone_card = Card.from_id(self.card_id)
        clone_card.color = self.color
        clone_card.skill.color = self.skill.color
        clone_card.base_vo = self.base_vo
        clone_card.base_da = self.base_da
        clone_card.base_vi = self.base_vi
        clone_card.base_li = self.base_li
        clone_card.skill.duration = self.skill.duration
        clone_card.skill.interval = self.skill.interval
        clone_card.vo_pots = self.vo_pots
        clone_card.da_pots = self.da_pots
        clone_card.vi_pots = self.vi_pots
        clone_card.li_pots = self.li_pots
        clone_card.sk_pots = self.sk_pots
        clone_card.star = self.star
        return clone_card

    def refresh_values(self):
        self.is_refreshed = True
        card_data = db.masterdb.execute_and_fetchone(
            """
            SELECT * FROM {} WHERE id = ?
            """.format("card_data"),
            params=[self.card_id],
            out_dict=True)

        bonuses = [card_data['bonus_vocal'], card_data['bonus_visual'], card_data['bonus_dance'],
                   card_data['bonus_hp'], 0]

        rarity = card_data['rarity'] if card_data['rarity'] % 2 == 1 else card_data['rarity'] - 1
        attributes = ['vo', 'vi', 'da', 'li', 'sk']
        potentials = [self.vo_pots, self.vi_pots, self.da_pots, self.li_pots, self.sk_pots]
        for idx, key in enumerate(attributes):
            if potentials[idx] == 0:
                continue
            bonuses[idx] += db.masterdb.execute_and_fetchone("""
                            SELECT value_rare_{} FROM potential_value_{} WHERE potential_level = ?
                        """.format(rarity, key), [potentials[idx]])[0]
        self.vo = self.base_vo + bonuses[0]
        self.vi = self.base_vi + bonuses[1]
        self.da = self.base_da + bonuses[2]
        self.li = self.base_li + bonuses[3]
        self.sk.probability = self.sk.max_probability + bonuses[4]
        self.sk.cached_probability = self.sk.probability
        self.sk.original_unit_idx = None

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
    def total_potentials(self):
        return self.vo_pots + self.da_pots + self.vi_pots + self.li_pots + self.sk_pots

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

    def __eq__(self, other):
        if other is None or not isinstance(other, Card):
            return False
        return self.card_id == other.card_id and self.skill == other.skill
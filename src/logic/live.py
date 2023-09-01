import io
from abc import ABC, abstractmethod
from collections import OrderedDict

import numpy as np
import pandas as pd
import pyximport

import customlogger as logger
from db import db
from exceptions import NoLiveFoundException
from logic.search import card_query
from logic.unit import BaseUnit, Unit
from settings import MUSICSCORES_PATH
from static.appeal_presets import APPEAL_PRESETS
from static.color import Color
from static.note_type import NoteType
from static.song_difficulty import Difficulty

pyximport.install(language_level=3)


def classify_note(row):
    if row.type == 8:
        return NoteType.DAMAGE
    if row.type == 5:
        return NoteType.SLIDE
    if row.type == 4:
        return NoteType.TAP
    if row.type == 6 or row.type == 7:
        return NoteType.FLICK
    if row.status != 0:
        return NoteType.FLICK
    if row.type == 1:
        return NoteType.TAP
    if row.type == 2:
        return NoteType.LONG
    if row.type == 3:
        return NoteType.SLIDE


def classify_note_vectorized(row):
    rowtype = row.type.astype(np.int32) # to prevent crashing in 32-bit python
    return np.choose(rowtype - 3, [
        np.choose(row.status == 0, [NoteType.FLICK, np.choose(
            rowtype - 1, [NoteType.TAP, NoteType.LONG, NoteType.SLIDE], mode="clip")]),
        NoteType.TAP, NoteType.SLIDE, NoteType.FLICK, NoteType.FLICK, NoteType.DAMAGE], mode="clip")


def get_score_color(score_id):
    color = db.masterdb.execute_and_fetchall("SELECT live_data.type FROM live_data WHERE live_data.id = ?",
                                             [score_id])
    return Color(color - 1)


def fetch_chart(base_music_name, base_score_id, base_difficulty, event=False, skip_load_notes=False):
    assert base_difficulty in Difficulty
    difficulty = base_difficulty.value

    if not base_score_id:
        event_test_conditions = (int(event), int(not event))
        music_name = base_music_name.strip()
        music_name_test_conditions = [music_name] + ["{}%{}".format(music_name[:i], music_name[i + 1:])
                                                     for i in range(len(music_name))]
        score_ids = ()
        for music_name in music_name_test_conditions:
            for event in event_test_conditions:
                score_ids = db.masterdb.execute_and_fetchall(
                    """
                    SELECT live_data.id, live_data.type, live_detail.level_vocal
                    FROM live_data, live_detail WHERE live_data.music_data_id IN (
                        SELECT id FROM music_data WHERE name LIKE ?
                    ) AND event_type >= ? AND live_detail.live_data_id = live_data.id AND live_detail.difficulty_type = ?
                    """,
                    [music_name, event, difficulty]
                )
                if score_ids:
                    break
    else:
        if difficulty is not None:
            score_ids = db.masterdb.execute_and_fetchall(
                """
                SELECT live_data.id, live_data.type, live_detail.level_vocal
                FROM live_data
                INNER JOIN live_detail ON live_detail.live_data_id = live_data.id
                WHERE live_data.id = ? AND live_detail.difficulty_type = ?
                """, [base_score_id, difficulty]
            )

    for score_id, color, level in score_ids:
        flag = False
        with db.CustomDB(MUSICSCORES_PATH / "musicscores_m{:03d}.db".format(score_id)) as score_conn:
            row_data = score_conn.execute_and_fetchone(
                """
                SELECT * from blobs WHERE name = "musicscores/m{:03d}/{:d}_{:d}.csv"
                """.format(score_id, score_id, difficulty)
            )
            if row_data:
                flag = True
        if flag:
            break

    if len(score_ids) == 0 or not flag:
        raise NoLiveFoundException("Music {} difficulty {} not found".format(music_name, str(base_difficulty)))
    if skip_load_notes:
        return None, Color(color - 1), level, None
    notes_data = pd.read_csv(io.StringIO(row_data[1].decode()))
    duration = notes_data.iloc[-1]['sec']
    if difficulty == 6:
        notes_data = notes_data[
            (notes_data["type"] < 8) & ((notes_data["visible"].isna()) | (notes_data["visible"] >= 0))].reset_index(
            drop=True)
    else:
        notes_data = notes_data[notes_data["type"] < 8].reset_index(drop=True)
    notes_data = notes_data.drop(["id"], axis=1)
    notes_data['note_type'] = notes_data.apply(classify_note, axis=1)
    return notes_data, Color(color - 1), level, duration


class BaseLive(ABC):

    def __init__(self, music_name=None, difficulty=None, unit=None):
        self.attributes = None
        self.extra_bonuses = None
        self.color_bonuses = None
        self.chara_bonus_set = {}
        self.chara_bonus_value = 0
        self.special_option = None
        self.special_value = None
        self.support = None
        self.unit = None
        self.music_name = None
        self.score_id = None
        self.difficulty = None
        self.notes = None
        self.color = None
        self.duration = None
        self.level = None
        self.initialize_music(music_name, difficulty, unit)

    def initialize_music(self, music_name=None, difficulty=None, unit=None):
        if music_name is not None and difficulty is not None:
            self.set_music(music_name, difficulty)
        if unit is not None:
            self.set_unit(unit)
        if self.unit is not None and self.color is not None:
            self.unit.skill_check(self.color)

    def get_support(self):
        if self.support is not None:
            return self.support[:, -1].sum()
        # Get all owned cards
        all_owned = db.cachedb.execute_and_fetchall("SELECT * FROM owned_card WHERE number > 0")
        all_owned = OrderedDict({_[0]: _[1] for _ in all_owned})

        # Remove one from unit
        queue_for_delete = list()
        for card in self.unit.all_cards():
            card = card.card_id
            if card in all_owned:
                all_owned[card] -= 1
                if all_owned[card] == 0:
                    queue_for_delete.append(card)
        for card in queue_for_delete:
            all_owned.pop(card)

        # Get appeals of all support cards
        query_result = db.cachedb.execute_and_fetchall("""
            SELECT
                attribute,
                vocal_max + bonus_vocal AS vocal,
                visual_max + bonus_visual AS visual,
                dance_max + bonus_dance AS dance
            FROM card_data_cache WHERE id IN ({})
            ORDER BY id
        """.format(",".join(map(str, all_owned.keys()))))

        # Evaluate support appeals
        base_support_attributes = np.zeros((len(query_result), 3, 3))  # Cards x Attributes x Colors
        for idx, (attribute, vocal, visual, dance) in enumerate(query_result):
            base_support_attributes[idx, 0, attribute - 1] += vocal
            base_support_attributes[idx, 1, attribute - 1] += visual
            base_support_attributes[idx, 2, attribute - 1] += dance
        bonuses = self.get_extra_bonuses() + self.get_color_bonuses()
        support_attributes = np.ceil(base_support_attributes * (1 + bonuses[:3] / 100) / 2)
        support_attributes *= 1 - (bonuses[:3] < -5000)
        support_attributes = support_attributes.sum(axis=2)  # Sum over colors

        # Temp is No. owned | Card ID | Vocal | Dance | Visual | Total
        temp = np.zeros((len(all_owned), 6))
        temp[:, 0] = list(all_owned.values())
        temp[:, 1] = list(all_owned.keys())
        temp[:, 2:5] = support_attributes
        temp[:, 5] = support_attributes.sum(axis=1)
        # Sort by total appeal
        temp = temp[temp[:, 5].argsort()[::-1]]
        # Get only cards that contribute to support
        last_idx = np.searchsorted(temp[:, 0].cumsum(), 10)
        # Duplicate cards that are starranked
        for i in reversed(range(last_idx + 1)):
            try:
                temp = np.insert(temp, [i + 1] * (int(temp[i, 0]) - 1), temp[i], axis=0)
            except IndexError:
                continue
        self.support = temp[:10, 1:].astype(int)  # Return top 10
        return self.support[:, -1].sum()

    def print_support_team(self):
        if self.support is None:
            self.get_support()
        return card_query.convert_id_to_short_name(" ".join(map(str, self.support[:, 0])))

    def set_music(self, music_name=None, score_id=None, difficulty=None, event=None, skip_load_notes=False):
        self.music_name = music_name
        if isinstance(difficulty, int):
            difficulty = Difficulty(difficulty)
        self.difficulty = difficulty
        self.score_id = score_id
        self.reset_attributes()
        if event is None:
            try:
                self.notes, self.color, self.level, self.duration = fetch_chart(music_name, score_id, difficulty,
                                                                                event=False,
                                                                                skip_load_notes=skip_load_notes)
            except ValueError:
                self.notes, self.color, self.level, self.duration = fetch_chart(music_name, score_id, difficulty,
                                                                                event=True,
                                                                                skip_load_notes=skip_load_notes)
        else:
            self.notes, self.color, self.level, self.duration = fetch_chart(music_name, score_id, difficulty,
                                                                            event=True, skip_load_notes=skip_load_notes)

    def set_extra_bonus(self, bonuses, special_option, special_value):
        self.extra_bonuses = bonuses
        self.special_option = special_option
        self.special_value = special_value
        if self.special_option == APPEAL_PRESETS["Event Idols"]:
            self.chara_bonus_value = special_value

    def attribute_cache_check(self):
        do_reset_attribute = False
        for card in self.unit.all_cards():
            if card.is_refreshed:
                do_reset_attribute = True
                card.is_refreshed = False
        if do_reset_attribute:
            self.reset_attributes(hard_reset=False)

    def get_extra_bonuses(self):
        if self.extra_bonuses is None:
            self.extra_bonuses = np.zeros((5, 3))
        return self.extra_bonuses

    def get_color_bonuses(self):
        self.color_bonuses = np.zeros((5, 3))
        if self.color is None:
            pass
        elif self.color == Color.ALL:
            self.color_bonuses[:3] = 30  # Appeal
            self.color_bonuses[4] = 30  # Skill
        else:
            self.color_bonuses[:3, self.color.value] = 30  # Appeal
            self.color_bonuses[4, self.color.value] = 30  # Skill
        return self.color_bonuses

    def set_chara_bonus(self, chara_bonus_set, chara_bonus_value):
        if chara_bonus_set is None:
            chara_bonus_set = set()
        self.chara_bonus_set = chara_bonus_set
        if chara_bonus_value is None:
            chara_bonus_value = 0
        self.chara_bonus_value = chara_bonus_value

    def get_appeals(self):
        return self.get_attributes()[:3].sum()

    @abstractmethod
    def get_bonuses(self):
        pass

    @abstractmethod
    def reset_attributes(self, hard_reset=True):
        pass

    @abstractmethod
    def set_unit(self, unit: BaseUnit):
        pass

    @abstractmethod
    def get_probability(self, idx=None):
        pass

    @abstractmethod
    def get_attributes(self):
        pass

    @abstractmethod
    def get_life(self):
        pass

    def get_start_life(self, doublelife=False):
        if doublelife:
            return self.get_life() * 2
        else:
            return self.get_life()

    @property
    @abstractmethod
    def is_grand(self):
        pass

    @property
    def is_grand_chart(self):
        return self.difficulty == Difficulty.PIANO or self.difficulty == Difficulty.FORTE


class Live(BaseLive):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.bonuses = None
        self.leader_bonuses = None
        self.probabilities = None
        self.fan = 0

    def set_unit(self, unit: Unit):
        self.unit = unit
        self.reset_attributes()

    def get_attributes(self):
        self.attribute_cache_check()
        if self.attributes is not None:
            return self.attributes
        self.get_bonuses()
        bonuses = self.bonuses.copy()
        self.apply_complex_bonus(bonuses)
        bonuses = np.clip(bonuses, a_min=-100, a_max=5000)
        bonuses = (1 + bonuses / 100)[:, :4, :]

        self.attributes = np.ceil(self.unit.base_attributes * bonuses).sum(axis=0)
        self.attributes *= 1 - (self.extra_bonuses[:4, :] < -5000)
        self.attributes = self.attributes.sum(axis=1)
        return self.attributes

    def reset_attributes(self, hard_reset=True):
        self.attributes = None  # Reset calculation
        self.bonuses = None
        if hard_reset:
            self.extra_bonuses = None
            self.chara_bonus_set = {}
            self.chara_bonus_value = 0
        self.leader_bonuses = None
        self.fan = 0
        self.support = None

    def get_life(self):
        return self.get_attributes()[3]

    @property
    def is_grand(self):
        return False

    def get_leader_bonuses(self):
        if self.leader_bonuses is None:
            bonuses, fan = self.unit.leader_bonuses(song_color=self.color, get_fan_bonuses=True)
            self.leader_bonuses = bonuses
            self.fan = fan
        return self.leader_bonuses

    def get_bonuses(self):
        if self.bonuses is not None:
            return
        bonuses = np.zeros((5, 3))
        bonuses += self.get_leader_bonuses()
        bonuses += self.get_color_bonuses()
        bonuses += self.get_extra_bonuses()
        bonuses[:3] += 10  # Furniture
        bonuses = np.repeat(bonuses[np.newaxis, :, :], self.unit.base_attributes.shape[0], axis=0)
        self.bonuses = bonuses

    def apply_complex_bonus(self, bonuses):
        if self.special_option == APPEAL_PRESETS["Event Idols"]:
            for card_idx, card in enumerate(self.unit.all_cards(guest=True)):
                if card.chara_id in self.get_chara_bonus_set():
                    bonuses[card_idx, :3, :] += self.chara_bonus_value
        elif self.special_option == APPEAL_PRESETS["Scale with Potential"]:
            for card_idx, card in enumerate(self.unit.all_cards(guest=True)):
                bonuses[card_idx, :3, :] += card.total_potentials * self.special_value
        elif self.special_option == APPEAL_PRESETS["Scale with Life"]:
            life_bonuses = 1 + self.bonuses[:, 3, :] / 100
            total_life = np.ceil(self.unit.base_attributes[:, 3, :] * life_bonuses).sum()
            booth_life_value = db.masterdb.execute_and_fetchall("""
                SELECT param, value FROM carnival_booth_life_value ORDER BY param
            """)
            last_bonus = 0
            for life, bonus in booth_life_value[1:]:
                if total_life < life:
                    bonuses[:, :3, :] += last_bonus
                    break
                else:
                    last_bonus = bonus - 100
        elif self.special_option == APPEAL_PRESETS["Scale with Star Rank"]:
            starrank_value = db.masterdb.execute_and_fetchall("""
                SELECT param, value_1, value_2, value_3, value_4 FROM carnival_booth_starrank_value ORDER BY param
            """)
            starrank_value_array = list()
            for i in range(20):
                temp = list()
                for j in range(4):
                    temp.append(starrank_value[i][j + 1] - 100)
                starrank_value_array.append(temp)
            for card_idx, card in enumerate(self.unit.all_cards(guest=True)):
                bonuses[card_idx, :3, :] += starrank_value_array[card.star - 1][card.rarity // 2 - 1]

    def get_probability(self, idx=None):
        if self.probabilities is None:
            card_probabilities = np.zeros((5, 3))
            for card_idx, card in enumerate(self.unit.all_cards()):
                card_probabilities[card_idx, card.color.value] = card.skill.probability
            self.get_bonuses()
            probability_bonus = self.bonuses[idx, 4, :]
            card_probabilities = (card_probabilities * (1 + probability_bonus / 100) / 10000).max(axis=1)
            logger.debug("Card probabilities: {}".format(card_probabilities))
            self.probabilities = np.clip(card_probabilities, a_min=0, a_max=1)
        if idx is None:
            return self.probabilities
        return self.probabilities[idx]

    def get_chara_bonus_set(self):
        if self.chara_bonus_set:
            return self.chara_bonus_set
        self.chara_bonus_set = Live.static_get_chara_bonus_set()
        return self.chara_bonus_set

    @classmethod
    def static_get_chara_bonus_set(cls, get_name=False):
        id_set = set(list(zip(*db.masterdb.execute_and_fetchall("SELECT chara_id FROM carnival_performer_idol")))[0])
        if get_name:
            return set(list(zip(*db.cachedb.execute_and_fetchall(
                "SELECT full_name FROM chara_cache WHERE chara_id IN ({})".format(",".join(map(str, id_set))))))[0])
        else:
            return id_set

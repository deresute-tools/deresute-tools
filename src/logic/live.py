import io
from collections import OrderedDict

import numpy as np
import pandas as pd

from logic.search import card_query
from settings import MUSICSCORES_PATH
from src import customlogger as logger
from src.db import db
from src.exceptions import NoLiveFoundException
from src.static.color import Color
from src.static.note_type import NoteType
from src.static.song_difficulty import Difficulty


def classify_note(row):
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


def get_score_color(score_id):
    color = db.masterdb.execute_and_fetchall("SELECT live_data.type FROM live_data WHERE live_data.id = ?",
                                             [score_id])
    return Color(color - 1)


def fetch_chart(base_music_name, base_score_id, base_difficulty, event=False):
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
                    ) AND event_type = ? AND live_detail.live_data_id = live_data.id AND live_detail.difficulty_type = ?
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
    notes_data = pd.read_csv(io.StringIO(row_data[1].decode()))
    duration = notes_data.iloc[-1]['sec']
    notes_data = notes_data[notes_data["type"] < 10].reset_index(drop=True)
    notes_data = notes_data.drop(["id"], axis=1)
    notes_data['note_type'] = notes_data.apply(classify_note, axis=1)
    return notes_data, Color(color - 1), level, duration


class Live:
    def __init__(self, music_name=None, difficulty=None, unit=None):
        self.attributes = None
        self.bonuses = None
        self.extra_bonuses = None
        self.leader_bonuses = None
        self.color_bonuses = None
        self.probabilities = None
        self.support = None
        self.unit = None
        self.music_name = None
        self.score_id = None
        self.difficulty = None
        self.notes = None
        self.color = None
        self.duration = None
        self.level = None
        if music_name is not None and difficulty is not None:
            self.set_music(music_name, difficulty)
        if unit is not None:
            self.set_unit(unit)

    def reset_attributes(self):
        self.attributes = None  # Reset calculation
        self.bonuses = None
        self.extra_bonuses = None
        self.leader_bonuses = None
        self.support = None

    def set_unit(self, unit):
        self.unit = unit
        self.reset_attributes()

    def set_music(self, music_name=None, score_id=None, difficulty=None, event=None):
        self.music_name = music_name
        if isinstance(difficulty, int):
            difficulty = Difficulty(difficulty)
        self.difficulty = difficulty
        self.score_id = score_id
        self.reset_attributes()
        if event is None:
            try:
                self.notes, self.color, self.level, self.duration = fetch_chart(music_name, score_id, difficulty,
                                                                                event=False)
            except ValueError:
                self.notes, self.color, self.level, self.duration = fetch_chart(music_name, score_id, difficulty,
                                                                                event=True)
        else:
            self.notes, self.color, self.level, self.duration = fetch_chart(music_name, score_id, difficulty,
                                                                            event=True)

    def set_extra_bonus(self, bonuses):
        self.extra_bonuses = np.zeros((5, 3))
        self.extra_bonuses[:3] = bonuses

    def get_bonuses(self):
        if self.bonuses is not None:
            return
        if not self.is_grand:
            self.leader_bonuses = self.unit.leader_bonuses(song_color=self.color)
        self.color_bonuses = np.zeros((5, 3))
        if self.extra_bonuses is None:
            self.extra_bonuses = np.zeros((5, 3))
        if self.color is None:
            pass
        elif self.color == Color.ALL:
            self.color_bonuses[:3] = 30  # Appeal
            self.color_bonuses[4] = 30  # Skill
        else:
            self.color_bonuses[:3, self.color.value] = 30  # Appeal
            self.color_bonuses[4, self.color.value] = 30  # Skill
        bonuses = np.zeros((5, 3))
        if not self.is_grand:
            bonuses = self.leader_bonuses
        bonuses += self.color_bonuses
        bonuses += self.extra_bonuses
        bonuses[:3] += 10  # Furniture
        self.bonuses = np.clip(bonuses, a_min=-100, a_max=5000)

    def get_attributes(self):
        if self.attributes is not None:
            return self.attributes
        self.get_bonuses()
        bonuses = (1 + self.bonuses / 100)[:4]
        self.attributes = np.ceil(self.unit.base_attributes * bonuses).sum(axis=0).sum(axis=1)
        return self.attributes

    def get_appeals(self):
        return self.get_attributes()[:3].sum()

    def get_life(self):
        return self.get_attributes()[3]

    def get_probability(self, idx=None):
        if self.probabilities is None:
            card_probabilities = np.zeros((5 * len(self.unit.all_units), 3))
            for unit_idx, unit in enumerate(self.unit.all_units):
                for card_idx, card in enumerate(unit.all_cards()):
                    card_probabilities[unit_idx * 5 + card_idx, card.color.value] = card.skill.probability
            self.get_bonuses()
            probability_bonus = self.bonuses[4]
            card_probabilities = (card_probabilities * (1 + probability_bonus / 100) / 10000).max(axis=1)
            logger.debug("Card probabilities: {}".format(card_probabilities))
            self.probabilities = np.clip(card_probabilities, a_min=0, a_max=1)
        if idx is None:
            return self.probabilities
        return self.probabilities[idx]

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
        self.get_bonuses()
        bonuses = self.extra_bonuses + self.color_bonuses
        support_attributes = np.ceil(base_support_attributes * (1 + bonuses[:3] / 100) / 2)
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
        for i in reversed(range(last_idx)):
            temp = np.insert(temp, [i + 1] * (int(temp[i, 0]) - 1), temp[i], axis=0)
        self.support = temp[:10, 1:].astype(int)  # Return top 10
        return self.support[:, -1].sum()

    def print_support_team(self):
        if self.support is None:
            self.get_support()
        return card_query.convert_id_to_short_name(" ".join(map(str, self.support[:, 0])))

    @property
    def is_grand(self):
        return False

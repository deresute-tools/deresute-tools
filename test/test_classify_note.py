import unittest
from io import StringIO

import pandas as pd

from db import db
from logic.live import classify_note, classify_note_vectorized
from network.chart_cache_updater import _get_song_list, _expand_song_list
from settings import MUSICSCORES_PATH
import customlogger as logger


class ClassifyNote(unittest.TestCase):
    def test_classify_note(self):
        song_list = _get_song_list()
        expanded_song_list = _expand_song_list(song_list)
        live_detail_ids = {_[0] for _ in
                                  db.cachedb.execute_and_fetchall("SELECT live_detail_id FROM live_detail_cache")}
        for ldid in live_detail_ids:
            live_data = expanded_song_list[ldid]
            with db.CustomDB(MUSICSCORES_PATH / "musicscores_m{:03d}.db".format(live_data["live_id"])) as score_conn:
                try:
                    score = score_conn.execute_and_fetchone(
                        """
                        SELECT * FROM blobs WHERE name LIKE "musicscores/m{:03d}/{:d}_{:d}.csv"
                        """.format(live_data["live_id"], live_data["live_id"], live_data["diff"])
                    )[1]
                except TypeError:
                    logger.debug(
                        "Cannot find chart for live detail ID {} difficulty {}".format(ldid, live_data["diff"]))
                    continue

            notes_data = pd.read_csv(StringIO(score.decode()))
            live_data["duration"] = notes_data.iloc[-1]['sec']
            notes_data = notes_data[notes_data["type"] < 10].reset_index(drop=True)
            note_types = notes_data.apply(classify_note, axis=1)
            note_types_vectorized = classify_note_vectorized(notes_data)
            self.assertTrue((note_types == note_types_vectorized).all(),
                            msg=f'Failed for ldid={ldid} (live_id={live_data["live_id"]}, diff={live_data["diff"]}')


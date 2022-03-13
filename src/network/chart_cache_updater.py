import logging
import sqlite3
from collections import OrderedDict, defaultdict
from io import StringIO

import numpy as np
import pandas as pd
import requests

import customlogger as logger
from db import db
from logic.live import classify_note_vectorized
from logic.skill import COMMON_TIMERS
from network import meta_updater
from settings import REMOTE_TRANSLATED_SONG_URL, REMOTE_CACHE_SCORES_URL, MUSICSCORES_PATH
from static.live_values import WEIGHT_RANGE
from static.note_type import NoteType

BLACKLIST = "1901,1902,1903,1904,90001"


def _check_remote_cache(url):
    initialize_score_db()
    response = requests.get(url)
    if response.status_code == 404:
        logger.debug("No remote live detail cache found at {}".format(url))
        return
    df = pd.read_csv(StringIO(response.content.decode("utf-8")))
    logger.debug("Remote live detail cache found at {}, {} rows".format(url, len(df)))
    for _, row in df.iterrows():
        _insert_into_live_detail_cache(row)
    db.cachedb.commit()


def _get_translated_name_df():
    response = requests.get(REMOTE_TRANSLATED_SONG_URL)
    df = pd.read_csv(StringIO(response.content.decode("utf-8")))
    return {
        r['id']: r['name'] for _, r in df.iterrows()
    }


def _get_song_list():
    translated_names = _get_translated_name_df()

    db.masterdb.execute("""ATTACH DATABASE "{}" AS cachedb""".format(meta_updater.get_cachedb_path()))
    db.masterdb.commit()

    res = db.masterdb.execute_and_fetchall("SELECT id, name FROM music_data WHERE id NOT IN ({})".format(BLACKLIST))
    song_dict = OrderedDict()
    for song_id, song_name in res:
        song_name = song_name.replace("\\n", "")
        if song_name not in song_dict:
            song_dict[song_name] = {
                'song_id_list': list()
            }
        song_dict[song_name]['song_id_list'].append(song_id)
    carnival_set_list = _get_carnival_set_list()
    for song_name, value in song_dict.items():
        live_list = list()
        for song_id in value['song_id_list']:
            query_res = db.masterdb.execute_and_fetchall("""
                            SELECT
                                id AS id,
                                difficulty_1    AS d1,
                                difficulty_2    AS d2,
                                difficulty_3    AS d3,
                                difficulty_4    AS d4,
                                difficulty_5    AS d5,
                                difficulty_11   AS d11,
                                difficulty_12   AS d12,
                                difficulty_21   AS d21,
                                difficulty_22   AS d22,
                                difficulty_101  AS d101,
                                CASE
                                    WHEN event_type == 1 
                                    THEN "Atapon"
                                    WHEN event_type == 3 
                                    THEN "Groove"
                                    WHEN event_type == 5 
                                    THEN "Parade"
                                    WHEN event_type == 7 
                                    THEN "Carnival"
                                    ELSE ""
                                END event_type,
                                type AS color
                                FROM live_data
                                WHERE music_data_id = ?
                        """, (song_id,), out_dict=True)
            live_list.extend(query_res)
        live_dict = _merge_live_list(live_list)
        for k, v in live_dict.items():
            value[k] = v
        value['sort'] = min(value.pop('song_id_list'))
        performers = db.masterdb.execute_and_fetchall("""
                        SELECT 
                            cc.full_name
                        FROM music_vocalist
                        LEFT JOIN cachedb.chara_cache cc ON cc.chara_id = music_vocalist.chara_id
                        WHERE music_data_id = ?
                    """, (value['sort'],))
        value['performers'] = ", ".join([_[0] for _ in performers])
        value['special_keys'] = _get_special_keys(value['sort'])
        for live_id in [_['id'] for _ in live_list]:
            if live_id in carnival_set_list.keys():
                if value['special_keys'] != "":
                    value['special_keys'] += ","
                value['special_keys'] += carnival_set_list[live_id]
                break
        value['jp_name'] = song_name
        if value['sort'] in translated_names:
            value['name'] = translated_names[value['sort']]
        else:
            value['name'] = song_name
    db.masterdb.execute("DETACH DATABASE cachedb")
    db.masterdb.commit()
    return song_dict


def _get_carnival_set_list():
    RANK_STRING = {
        1: "d3",
        2: "d2",
        3: "d1",
        4: "c3",
        5: "c2",
        6: "c1",
        7: "b3",
        8: "b2",
        9: "b1",
        10: "a3",
        11: "a2",
        12: "a1",
        13: "s",
        14: "ss",
        15: "sss",
    }
    query = """
    SELECT 
        carnival_map.rank,
        carnival_map.booth_id,
        carnival_map.value2,
        carnival_setlist.live_id
    FROM carnival_map
    LEFT JOIN carnival_setlist ON carnival_setlist.setlist_id = carnival_map.value2
    WHERE carnival_map.value2 > 0 AND carnival_map.rank > 0
    """
    res = db.masterdb.execute_and_fetchall(query)
    ret_dict = dict()
    for rank, booth_id, _, live_id in res:
        ret_dict[live_id] = "carnival" + RANK_STRING[rank] + str(booth_id)
    return ret_dict


def _get_special_keys(song_id):
    if 3200 > song_id > 3000:
        return "solo"
    if 3300 > song_id > 3200:
        return "solo2"
    if 8000 > song_id > 7000:
        return "mix"
    if 9000 > song_id > 8000:
        return "collab"
    return ""


def _merge_live_list(live_list):
    if len(live_list) == 1:
        release = live_list[0]
        event = defaultdict(int)
    else:
        if live_list[0]['event_type'] == '':
            release = live_list[0]
            event = live_list[1]
        else:
            release = live_list[1]
            event = live_list[0]
    res_dict = OrderedDict()
    res_dict['diff'] = list()
    for diff in ["d1", "d2", "d3", "d4", "d5", "d11", "d12", "d21", "d22", "d101"]:
        if release[diff] == 0:
            live_detail_id = event[diff]
            live_id = event['id']
        else:
            live_detail_id = release[diff]
            live_id = release['id']
        if live_detail_id != 0:
            res_dict['diff'].append((diff, live_detail_id, live_id))
    res_dict['color'] = release['color']
    return res_dict


def _expand_song_list(song_list):
    res_dict = dict()
    for value in song_list.values():
        for diff, live_detail_id, live_id in value['diff']:
            res_dict[live_detail_id] = dict(value)
            res_dict[live_detail_id].pop("diff")
            res_dict[live_detail_id]['live_detail_id'] = live_detail_id
            res_dict[live_detail_id]['live_id'] = live_id
            res_dict[live_detail_id]['diff'] = int(diff[1:])
            res_dict[live_detail_id]['level'] = \
                db.masterdb.execute_and_fetchone("SELECT level_vocal FROM live_detail WHERE live_detail.id = ?",
                                                 (live_detail_id,))[0]
    return res_dict


def initialize_score_db():
    db.cachedb.execute("""
        CREATE TABLE IF NOT EXISTS live_detail_cache (
            live_detail_id INTEGER UNIQUE PRIMARY KEY,
            live_id INTEGER NOT NULL,
            sort INTEGER NOT NULL,
            color INTEGER NOT NULL,
            performers TEXT,
            special_keys TEXT,
            jp_name TEXT NOT NULL,
            name TEXT NOT NULL,
            difficulty INTEGER NOT NULL,
            level INTEGER NOT NULL,
            duration FLOAT NOT NULL,
            Tap INTEGER NOT NULL,
            Long INTEGER NOT NULL,
            Flick INTEGER NOT NULL,
            Slide INTEGER NOT NULL,
            Timer_7h REAL NOT NULL,
            Timer_9h REAL NOT NULL,
            Timer_11h REAL NOT NULL,
            Timer_12m REAL NOT NULL,
            Timer_6m REAL NOT NULL,
            Timer_9m REAL NOT NULL,
            Timer_11m REAL NOT NULL,
            Timer_13h REAL NOT NULL
        )
    """)
    db.cachedb.commit()


def has_cached_live_details():
    try:
        db.cachedb.execute_and_fetchall("SELECT * FROM live_detail_cache")
        return True
    except sqlite3.OperationalError:
        logger.debug("No local cached live details found")
        return False


def _insert_into_live_detail_cache(hashable):
    db.cachedb.execute("""
            INSERT OR IGNORE INTO live_detail_cache( live_detail_id, live_id, sort, color, performers, special_keys,
             jp_name, name, difficulty, level, duration, Tap, Long, Flick, Slide,
             Timer_7h, Timer_9h, Timer_11h, Timer_12m, Timer_6m, Timer_9m, Timer_11m, Timer_13h)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """, [
        hashable["live_detail_id"],
        hashable["live_id"],
        hashable["sort"],
        hashable["color"],
        hashable["performers"],
        hashable["special_keys"],
        hashable["jp_name"],
        hashable["name"],
        hashable["difficulty"],
        hashable["level"],
        hashable["duration"],
        hashable["Tap"],
        hashable["Long"],
        hashable["Flick"],
        hashable["Slide"],
        hashable["Timer_7h"],
        hashable["Timer_9h"],
        hashable["Timer_11h"],
        hashable["Timer_12m"],
        hashable["Timer_6m"],
        hashable["Timer_9m"],
        hashable["Timer_11m"],
        hashable["Timer_13h"]
    ])


def _overwrite_song_name(expanded_song_list):
    for live_detail_id, song_data in expanded_song_list.items():
        db.cachedb.execute("""
                    UPDATE live_detail_cache
                    SET name = ?, special_keys = ?
                    WHERE live_detail_id = ?
                """, [
            song_data["name"],
            song_data["special_keys"],
            live_detail_id,
        ])
    db.cachedb.commit()


def _is_active(time, interval, duration, last_note):
    return (time > interval) & (time % interval < duration) & (time // interval * interval <= last_note - 3)


def update_cache_scores():
    if not has_cached_live_details():
        initialize_score_db()
    song_list = _get_song_list()
    expanded_song_list = _expand_song_list(song_list)
    cached_live_detail_ids = {_[0] for _ in
                              db.cachedb.execute_and_fetchall("SELECT live_detail_id FROM live_detail_cache")}
    new_live_detail_ids = set(expanded_song_list.keys()).difference(cached_live_detail_ids)
    logger.debug("Uncached live detail IDs: {}".format(new_live_detail_ids))
    for ldid in new_live_detail_ids:
        live_data = expanded_song_list[ldid]
        with db.CustomDB(MUSICSCORES_PATH / "musicscores_m{:03d}.db".format(live_data["live_id"])) as score_conn:
            try:
                score = score_conn.execute_and_fetchone(
                    """
                    SELECT * FROM blobs WHERE name LIKE "musicscores/m{:03d}/{:d}_{:d}.csv"
                    """.format(live_data["live_id"], live_data["live_id"], live_data["diff"])
                )[1]
            except TypeError:
                logger.debug("Cannot find chart for live detail ID {} difficulty {}".format(ldid, live_data["diff"]))
                continue
        notes_data = pd.read_csv(StringIO(score.decode()))
        live_data["duration"] = notes_data.iloc[-1]['sec']
        notes_data = notes_data[notes_data["type"] < 10].reset_index(drop=True)
        notes_data['note_type'] = classify_note_vectorized(notes_data)
        note_count = dict(notes_data['note_type'].value_counts())
        for note_type in NoteType:
            key_str = note_type.name.capitalize()
            if note_type in note_count:
                live_data[key_str] = int(note_count[note_type])
            else:
                live_data[key_str] = 0
        live_data['difficulty'] = live_data['diff']
        total_notes = len(notes_data)
        combo_thresholds = (total_notes * WEIGHT_RANGE[:, 0] / 100).astype(int)
        # Correct for deresute's rounding method
        combo_thresholds[1:-1] -= 1
        for timer in COMMON_TIMERS:
            live_data['Timer_{}{}'.format(timer[0], timer[2])] = np.repeat(
                WEIGHT_RANGE[:, 1], combo_thresholds[1:] - combo_thresholds[:-1]
            )[_is_active(notes_data['sec'], timer[0], timer[1], notes_data.iloc[-1]['sec'])].sum() / (
                    ((WEIGHT_RANGE[1:, 0] - WEIGHT_RANGE[:-1, 0]) * WEIGHT_RANGE[:-1, 1]).sum() / 100 * total_notes)
        _insert_into_live_detail_cache(live_data)
    _overwrite_song_name(expanded_song_list)
    db.cachedb.commit()


if __name__ == '__main__':
    logging.basicConfig(level=logging.CRITICAL,
                        format='%(asctime)s - %(levelname)s - %(module)s - %(message)s',
                        datefmt='%d-%b-%y %H:%M:%S')
    update_cache_scores()

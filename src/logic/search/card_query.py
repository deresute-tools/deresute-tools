import os
import sys
from collections import defaultdict

from db import db
from network import kirara_query
from static.rarity import Rarity
from utils.misc import is_debug_mode

ALIASES = {
    "santaclaus": "eve",
    "anastasia": "anya"
}

queried_to_kirara = False


def get_chara_dict():
    global queried_to_kirara
    # Prevent query if debugging
    if not queried_to_kirara and (
            not is_debug_mode() or not db.cachedb.execute_and_fetchone("""
            SELECT name FROM sqlite_master WHERE type='table' AND name='chara_cache'
        """)):
        kirara_query.update_chara_data()
        # Prevent redundant queries
        queried_to_kirara = True
    results = db.cachedb.execute_and_fetchall("""
        SELECT chara_id, conventional FROM chara_cache
    """)
    return {_: __ for _, __ in results}


def generate_short_names():
    chara_data_dict = get_chara_dict()
    card_chara_rarity = db.masterdb.execute_and_fetchall(
        """
        SELECT chara_id, GROUP_CONCAT(id), GROUP_CONCAT(rarity)
        FROM card_data
        GROUP BY chara_id
        """
    )
    db.cachedb.execute("""
        CREATE TABLE IF NOT EXISTS card_name_cache (
        card_id TEXT UNIQUE PRIMARY KEY,
        chara_id INTEGER NOT NULL,
        card_rarity INTEGER NOT NULL,
        card_short_name TEXT NOT NULL,
        FOREIGN KEY (chara_id) REFERENCES chara_cache(chara_id) 
        )
    """)
    for chara_id, card_ids, card_rarities in card_chara_rarity:
        if chara_id not in chara_data_dict:
            continue
        chara_name = chara_data_dict[chara_id]
        if chara_name in ALIASES:
            chara_name = ALIASES[chara_name]
        card_ids = card_ids.split(",")
        card_rarities = card_rarities.split(",")
        card_rarities = list(map(lambda x: Rarity(int(x)), card_rarities))
        rarity_count = defaultdict(int)
        temp = list()
        for card_rarity in card_rarities:
            rarity_count[card_rarity] += 1
            if card_rarity == Rarity.SSR or card_rarity == Rarity.SSRU:
                short_name = chara_name
            else:
                short_name = chara_name + card_rarity.name.lower()
            if card_rarity in {Rarity.NU, Rarity.RU, Rarity.SRU}:
                short_name = short_name[:-1] + str(rarity_count[card_rarity]) + short_name[-1]
            elif card_rarity == Rarity.SSRU:
                short_name = short_name + str(rarity_count[card_rarity]) + "u"
            else:
                short_name = short_name + str(rarity_count[card_rarity])
            temp.append(short_name)
        for card_id, card_rarity, short_name in zip(card_ids, card_rarities, temp):
            db.cachedb.execute("""
                INSERT OR REPLACE INTO card_name_cache (card_id,chara_id,card_rarity,card_short_name)
                VALUES (?,?,?,?)
            """, [card_id, chara_id, card_rarity.value, short_name])
    db.cachedb.commit()


def convert_short_name_to_id(query):
    if isinstance(query, list):
        tokens = query
    elif isinstance(query, str):
        tokens = query.split()
    else:
        raise ValueError("Invalid query: {}".format(query))
    results = list()
    for token in tokens:
        if token.isdigit():
            results.append(int(token))
        else:
            results.append(int(
                db.cachedb.execute_and_fetchone("""
                    SELECT card_id FROM card_name_cache WHERE card_short_name IN (?);
                """, [token])[0]
            ))
    return results


def convert_id_to_short_name(query):
    if isinstance(query, list):
        tokens = query
    elif isinstance(query, str):
        tokens = query.split()
    else:
        raise ValueError("Invalid query: {}".format(query))
    results = list()
    for token in tokens:
        query_res = db.cachedb.execute_and_fetchone("""
                SELECT card_short_name FROM card_name_cache WHERE card_id IN (?);
            """, [token])
        query_res = query_res[0] if query_res is not None else "MyCard"
        results.append(query_res)
    return results


generate_short_names()

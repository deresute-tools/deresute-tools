import pandas as pd

from src.db import db
from src.logic.search import card_query

chara_dict = card_query.get_chara_dict()


def initialize_potential_db():
    db.cachedb.execute("DROP TABLE IF EXISTS potential_cache")
    db.cachedb.execute("""
        CREATE TABLE potential_cache (
            chara_id INTEGER PRIMARY KEY,
            vo INTEGER NOT NULL,
            vi INTEGER NOT NULL,
            da INTEGER NOT NULL,
            li INTEGER NOT NULL,
            sk INTEGER NOT NULL,
            FOREIGN KEY (chara_id) REFERENCES chara_cache(chara_id) 
        )
    """)
    db.cachedb.commit()


def copy_card_data_from_master(update_all=True, chara_id=None):
    if update_all:
        db.cachedb.execute("DROP TABLE IF EXISTS card_data_cache")
        all_cards = db.masterdb.execute_and_fetchall("SELECT * FROM card_data", out_dict=True)
    else:
        assert chara_id is not None
        all_cards = db.masterdb.execute_and_fetchall("SELECT * FROM card_data WHERE chara_id = ?", [chara_id],
                                                     out_dict=True)
    potentials = db.cachedb.execute_and_fetchall("SELECT * FROM potential_cache", out_dict=True)
    card_df = pd.DataFrame(all_cards)
    pot_df = pd.DataFrame(potentials)
    attributes = [('vo', 'vocal'),
                  ('vi', 'visual'),
                  ('da', 'dance'),
                  ('li', 'hp'),
                  ('sk', 'skill')]
    card_df = card_df.merge(pot_df, on='chara_id', how='left')
    pots = {
        key: pd.read_sql_query("SELECT * FROM potential_value_{}".format(key),
                               db.masterdb.get_connection())
        for key, _ in attributes
    }
    for rarity in range(4):
        rarity1 = rarity * 2 + 1
        rarity2 = rarity * 2 + 2
        for key, full_name in attributes:
            pot_map = dict(zip(pots[key]['potential_level'], pots[key]['value_rare_{}'.format(rarity1)]))
            pot_map[0] = 0
            card_df.loc[(card_df['rarity'] == rarity1) | (card_df['rarity'] == rarity2), key] = card_df.loc[
                (card_df['rarity'] == rarity1) | (card_df['rarity'] == rarity2), key].map(pot_map)
    card_df['bonus_skill'] = 0
    for key, full_name in attributes:
        card_df['bonus_{}'.format(full_name)] += card_df[key]
    card_df = card_df.drop([_[0] for _ in attributes], axis=1)
    if update_all:
        card_df.to_sql('card_data_cache', db.cachedb.get_connection(), index=False)
    else:
        db.cachedb.execute("DELETE FROM card_data_cache WHERE chara_id = ?", [chara_id])
        card_df.to_sql('card_data_cache', db.cachedb.get_connection(), if_exists='append', index=False)
    db.cachedb.commit()


def update_potential(chara_id, pots):
    assert len(pots) == 5
    db.cachedb.execute("""
        INSERT OR REPLACE INTO potential_cache (chara_id, vo, vi, da, li, sk)
        VALUES (?,?,?,?,?,?)
    """, [int(chara_id)] + list(map(int, pots)))
    copy_card_data_from_master(update_all=False, chara_id=chara_id)

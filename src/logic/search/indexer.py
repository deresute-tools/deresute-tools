import ast
import shutil

from whoosh.fields import *
from whoosh.index import create_in

from settings import INDEX_PATH
from src import customlogger as logger
from src.db import db
from src.network.meta_updater import get_masterdb_path



KEYWORD_KEYS_STR_ONLY = ["short", "chara", "rarity", "color", "skill", "leader", "time_prob_key"]
KEYWORD_KEYS = KEYWORD_KEYS_STR_ONLY + ["owned", "idolized"]


class IndexManager:

    def __init__(self):
        if self.cleanup():
            INDEX_PATH.mkdir()
        self.index = None

    def initialize_index_db(self):
        db.cachedb.execute("""ATTACH DATABASE "{}" AS masterdb""".format(get_masterdb_path()))
        data = db.cachedb.execute_and_fetchall("""
            SELECT  cdc.id,
                    LOWER(cnc.card_short_name) as short,
                    oc.number as owned,
                    LOWER(cc.full_name) as chara,
                    LOWER(rt.text) as rarity,
                    LOWER(ct.text) as color,
                    CASE 
                        WHEN cdc.rarity % 2 == 0 THEN 1
                        ELSE 0
                    END idolized,
                    CASE 
                        WHEN pk.id IS NOT NULL THEN sd.condition || pk.short ELSE '' 
                    END time_prob_key, 
                    IFNULL(LOWER(sk.keywords), "") as skill,
                    IFNULL(LOWER(lk.keywords), "") as leader
            FROM card_data_cache as cdc
            INNER JOIN card_name_cache cnc on cdc.id = cnc.card_id
            INNER JOIN owned_card oc on oc.card_id = cnc.card_id
            INNER JOIN chara_cache cc on cdc.chara_id = cc.chara_id
            INNER JOIN rarity_text rt on cdc.rarity = rt.id
            INNER JOIN color_text ct on cdc.attribute = ct.id
            LEFT JOIN masterdb.skill_data sd on cdc.skill_id = sd.id
            LEFT JOIN probability_keywords pk on pk.id = sd.probability_type
            LEFT JOIN skill_keywords sk on sd.skill_type = sk.id
            LEFT JOIN leader_keywords lk on cdc.leader_skill_id = lk.id
        """, out_dict=True)
        db.cachedb.execute("DROP TABLE IF EXISTS card_index_keywords")
        db.cachedb.execute("""
            CREATE TABLE IF NOT EXISTS card_index_keywords (
                "card_id" INTEGER UNIQUE PRIMARY KEY,
                "fields" BLOB
            )
        """)
        for card in data:
            card_id = card['id']
            fields = {_: card[_] for _ in KEYWORD_KEYS}
            db.cachedb.execute("""
                    INSERT OR IGNORE INTO card_index_keywords ("card_id", "fields")
                    VALUES (?,?)
                """, [card_id, str(fields)])
        db.cachedb.commit()
        db.cachedb.execute("DETACH DATABASE masterdb")

    def initialize_index(self):
        results = db.cachedb.execute_and_fetchall("SELECT card_id, fields FROM card_index_keywords")
        schema = Schema(title=ID(stored=True),
                        idolized=BOOLEAN,
                        short=TEXT,
                        owned=NUMERIC,
                        chara=TEXT,
                        rarity=TEXT,
                        color=TEXT,
                        skill=TEXT,
                        leader=TEXT,
                        time_prob_key=TEXT,
                        content=TEXT)
        ix = create_in(INDEX_PATH, schema)
        writer = ix.writer()
        for result in results:
            fields = ast.literal_eval(result[1])
            content = " ".join([fields[key] for key in KEYWORD_KEYS_STR_ONLY])
            writer.add_document(title=str(result[0]),
                                content=content,
                                **fields)
        writer.commit()
        self.index = ix

    def reindex(self):
        results = db.cachedb.execute_and_fetchall("SELECT card_id, fields FROM card_index_keywords")
        writer = self.index.writer()
        for result in results:
            fields = ast.literal_eval(result[1])
            content = " ".join([fields[key] for key in KEYWORD_KEYS_STR_ONLY])
            writer.update_document(title=str(result[0]),
                                   content=content,
                                   **fields)
        writer.commit()

    def get_index(self):
        if self.index is None:
            im.initialize_index_db()
            im.initialize_index()
        return self.index

    def cleanup(self):
        try:
            if INDEX_PATH.exists():
                shutil.rmtree(str(INDEX_PATH))
            return True
            logger.debug("Index cleaned up.")
        except PermissionError:
            return False

    def __del__(self):
        if self.index is not None:
            self.index.close()


im = IndexManager()

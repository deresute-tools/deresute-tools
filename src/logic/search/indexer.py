import ast
import shutil

from whoosh.analysis import SimpleAnalyzer
from whoosh.fields import *
from whoosh.index import create_in

import customlogger as logger
from db import db
from logic.live import Live
from network.meta_updater import get_masterdb_path
from settings import INDEX_PATH
from static.color import Color
from static.song_difficulty import Difficulty

KEYWORD_KEYS_STR_ONLY = ["short", "chara", "rarity", "color", "skill", "leader", "time_prob_key", "fes", "noir",
                         "blanc", "carnival", "main_attribute"]
KEYWORD_KEYS = KEYWORD_KEYS_STR_ONLY + ["owned", "idolized"]


class IndexManager:

    def __init__(self):
        if self.cleanup():
            INDEX_PATH.mkdir()
        self.index = None
        self.song_index = None

    def initialize_index_db(self, card_list=None):
        logger.info("Building quicksearch index, please wait...")

        carnival_idols = ",".join(map(str, Live.static_get_chara_bonus_set(get_name=False)))

        db.cachedb.execute("""ATTACH DATABASE "{}" AS masterdb""".format(get_masterdb_path()))
        query = """
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
                    IFNULL(LOWER(lk.keywords), "") as leader,
                    CASE
                        WHEN cdc.leader_skill_id IN (70,71,72,73,81,82,83,84,104,105,106,113,117,118)
                        AND cdc.rarity > 6 
                        THEN "fes" 
                        ELSE ""
                    END fes,
                    CASE
                        WHEN cdc.leader_skill_id IN (70,71,72,73,81,82,83,84,104,105,106,113,117)
                        AND cdc.rarity > 6 
                        THEN "blanc"
                        ELSE ""
                    END blanc,
                    CASE
                        WHEN cdc.leader_skill_id IN (118)
                        AND cdc.rarity > 6 
                        THEN "noir"
                        ELSE ""
                    END noir,
                    CASE
                        WHEN cdc.chara_id IN ({})
                        THEN "carnival"
                        ELSE ""
                    END carnival,
                    CASE
                        WHEN 1.0 * cdc.vocal_min / (cdc.vocal_min + cdc.visual_min + cdc.dance_min) > 0.39 
                        THEN "vocal" 
                        WHEN 1.0 * cdc.visual_min / (cdc.vocal_min + cdc.visual_min + cdc.dance_min) > 0.39 
                        THEN "visual"
                        WHEN 1.0 * cdc.dance_min / (cdc.vocal_min + cdc.visual_min + cdc.dance_min) > 0.39 
                        THEN "dance"
                        ELSE "balance"
                    END main_attribute
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
        """.format(carnival_idols)
        if card_list is not None:
            query += "WHERE cdc.id IN ({})".format(','.join(['?'] * len(card_list)))
            data = db.cachedb.execute_and_fetchall(query, card_list, out_dict=True)
        else:
            data = db.cachedb.execute_and_fetchall(query, out_dict=True)
            db.cachedb.execute("DROP TABLE IF EXISTS card_index_keywords")
            db.cachedb.execute("""
                CREATE TABLE IF NOT EXISTS card_index_keywords (
                    "card_id" INTEGER UNIQUE PRIMARY KEY,
                    "fields" BLOB
                )
            """)
        logger.debug("Initializing quicksearch db for {} cards".format(len(data)))
        for card in data:
            card_id = card['id']
            fields = {_: card[_] for _ in KEYWORD_KEYS}
            db.cachedb.execute("""
                    INSERT OR REPLACE INTO card_index_keywords ("card_id", "fields")
                    VALUES (?,?)
                """, [card_id, str(fields)])
        db.cachedb.commit()
        logger.debug("Quicksearch db transaction for {} cards completed".format(len(data)))
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
                        carnival=TEXT,
                        leader=TEXT,
                        fes=TEXT,
                        noir=TEXT,
                        blanc=TEXT,
                        main_attribute=TEXT,
                        time_prob_key=TEXT,
                        content=TEXT(analyzer=SimpleAnalyzer()))
        ix = create_in(INDEX_PATH, schema)
        writer = ix.writer()
        logger.debug("Initializing quicksearch index for {} cards".format(len(results)))
        for result in results:
            fields = ast.literal_eval(result[1])
            content = " ".join([fields[key] for key in KEYWORD_KEYS_STR_ONLY])
            writer.add_document(title=str(result[0]),
                                content=content,
                                **fields)
        writer.commit()
        self.index = ix
        logger.debug("Quicksearch index initialized for {} cards".format(len(results)))

    def initialize_chart_index(self):
        results = db.cachedb.execute_and_fetchall(
            "SELECT live_detail_id, performers, special_keys, jp_name, name, level, color, difficulty FROM live_detail_cache")
        schema = Schema(title=ID(stored=True),
                        live_detail_id=NUMERIC,
                        performers=TEXT,
                        special_keys=TEXT,
                        jp_name=TEXT,
                        name=TEXT,
                        difficulty=TEXT,
                        level=NUMERIC,
                        color=TEXT,
                        content=TEXT(analyzer=SimpleAnalyzer()))
        ix = create_in(INDEX_PATH, schema, indexname="score")
        writer = ix.writer()
        logger.debug("Initializing quicksearch index for {} charts".format(len(results)))
        for result in results:
            difficulty = Difficulty(result[-1]).name.lower()
            performers = result[1].replace(",", "") if result[1] else ""
            color = Color(result[6] - 1).name.lower()
            content = " ".join(
                [performers, result[2] if result[2] else "", result[3], result[4], difficulty, color, str(result[5])])
            writer.add_document(title=str(result[0]),
                                content=content,
                                live_detail_id=result[0],
                                performers=performers,
                                special_keys=result[2],
                                jp_name=result[3],
                                name=result[4],
                                level=result[5],
                                color=color,
                                difficulty=difficulty,
                                )
        writer.commit()
        self.song_index = ix
        logger.debug("Quicksearch index initialized for {} charts".format(len(results)))

    def reindex(self, card_ids=None):
        logger.debug("Reindexing for {} cards".format(len(card_ids)))
        if card_ids is not None:
            results = db.cachedb.execute_and_fetchall(
                """
                SELECT card_id, fields 
                FROM card_index_keywords 
                WHERE card_id IN ({})
                """.format(','.join(['?'] * len(card_ids))), card_ids)
        else:
            results = db.cachedb.execute_and_fetchall("SELECT card_id, fields FROM card_index_keywords")
        writer = self.index.writer()
        for result in results:
            fields = ast.literal_eval(result[1])
            content = " ".join([fields[key] for key in KEYWORD_KEYS_STR_ONLY])
            writer.delete_by_term('title', str(result[0]))
            writer.add_document(title=str(result[0]),
                                content=content,
                                **fields)
        writer.commit()

    def get_index(self, song_index=False):
        if self.index is None:
            im.initialize_index_db()
            im.initialize_index()
            im.initialize_chart_index()
        if song_index:
            return self.song_index
        return self.index

    def cleanup(self):
        try:
            if INDEX_PATH.exists():
                shutil.rmtree(str(INDEX_PATH))
            logger.debug("Index cleaned up.")
            return True
        except PermissionError:
            return False

    def __del__(self):
        if self.index is not None:
            self.index.close()


im = IndexManager()

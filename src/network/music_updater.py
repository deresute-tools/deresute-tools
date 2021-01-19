import logging

import customlogger as logger
from db import db
from network import cgss_query
from network import meta_updater
from settings import MANIFEST_PATH, MUSICSCORES_PATH
from utils import storage
from utils.misc import decompress


def _score_cache_db_exists():
    return db.cachedb.execute_and_fetchone("""
        SELECT name FROM sqlite_master WHERE type='table' AND name='score_cache'
    """)


def _initialize_score_cache_db():
    db.cachedb.execute("""
        CREATE TABLE IF NOT EXISTS score_cache (
            score_id TEXT UNIQUE PRIMARY KEY,
            score_hash TEXT NOT NULL
        ) 
    """)
    db.cachedb.commit()


def update_musicscores():
    logger.debug("Updating all musicscores")
    if not storage.exists(MANIFEST_PATH):
        logger.debug("manifest.db not found, updating metadata")
        meta_updater.update_database()
    with db.CustomDB(meta_updater.get_manifestdb_path()) as manifest_conn:
        all_musicscores = manifest_conn.execute_and_fetchall(
            """
            SELECT name,hash FROM manifests WHERE (name LIKE "musicscores\_m___.bdb" ESCAPE '\\')
            """)
        all_musicscores = {_[0].split(".")[0]: _[1] for _ in all_musicscores}

    if not _score_cache_db_exists():
        _initialize_score_cache_db()
        new_scores = all_musicscores.keys()
        updated_scores = set()
    else:
        scores_meta = db.cachedb.execute_and_fetchall("SELECT score_id, score_hash FROM score_cache")
        scores_meta = {_: __ for _, __ in scores_meta}
        deleted_scores = set(scores_meta.keys()).difference(all_musicscores.keys())
        if len(deleted_scores) > 0:
            logger.info("Found {} defunct musicscores, removing them...".format(len(deleted_scores)))
            for deleted_score in deleted_scores:
                path = MUSICSCORES_PATH / "{}.db".format(deleted_score)
                path.unlink()
        new_scores = set(all_musicscores.keys()).difference(scores_meta.keys())
        updated_scores = [
            _
            for _ in set(all_musicscores.keys()).intersection(scores_meta.keys())
            if scores_meta[_] != all_musicscores[_]
        ]
    logger.info(
        "Found {} musicscores, {} of them are new, {} are updated...".format(len(all_musicscores), len(new_scores),
                                                                             len(updated_scores)))

    if len(new_scores) + len(updated_scores) > 50:
        logger.info("It will take some time to download, please wait...")

    for musicscore_name in set(new_scores).union(set(updated_scores)):
        musicscore_hash = all_musicscores[musicscore_name]
        musicscore_response = cgss_query.get_db(musicscore_hash)
        with storage.get_writer(MUSICSCORES_PATH / "{}.db".format(musicscore_name), 'wb') as fwb:
            fwb.write(decompress(musicscore_response.content))
        db.cachedb.execute("""
            INSERT OR REPLACE INTO score_cache (score_id, score_hash)
            VALUES (?,?)
        """, [musicscore_name, musicscore_hash])
    db.cachedb.commit()
    logger.info("All musicscores updated")


if __name__ == '__main__':
    logging.basicConfig(level=logging.CRITICAL,
                        format='%(asctime)s - %(levelname)s - %(module)s - %(message)s',
                        datefmt='%d-%b-%y %H:%M:%S')
    logger.setLevel(logging.DEBUG)
    update_musicscores()

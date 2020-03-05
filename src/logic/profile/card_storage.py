from src import customlogger as logger
from src.db import db


def initialize_owned_cards():
    db.cachedb.execute("DROP TABLE IF EXISTS owned_card")
    db.cachedb.execute("""
        CREATE TABLE owned_card (
            card_id INTEGER PRIMARY KEY UNIQUE,
            number INTEGER NOT NULL,
            FOREIGN KEY (card_id) REFERENCES card_data_cache(id)
        )
    """)
    db.cachedb.commit()


def update_owned_cards(card_ids, numbers):
    logger.info("Updating cards: {}".format(card_ids))
    if not isinstance(card_ids, list) or not isinstance(numbers, list):
        card_ids = [card_ids]
        numbers = [numbers]
    assert len(card_ids) == len(numbers)
    for card_id, number in zip(card_ids, numbers):
        db.cachedb.execute("""
            INSERT OR REPLACE INTO owned_card (card_id, number)
            VALUES (?,?)
        """, [card_id, number])
    db.cachedb.commit()
    from src.logic.search import indexer, search_engine
    indexer.im.initialize_index_db(card_ids)
    indexer.im.reindex(card_ids)
    search_engine.engine.refresh_searcher()

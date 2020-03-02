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


def update_owned_cards(card_id, number):
    db.cachedb.execute("""
        INSERT OR REPLACE INTO owned_card (card_id, number)
        VALUES (?,?)
    """, [card_id, number])

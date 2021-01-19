from enum import Enum

import customlogger as logger
from db import db


class Rarity(Enum):
    NU = 1
    N = 2
    RU = 3
    R = 4
    SRU = 5
    SR = 6
    SSRU = 7
    SSR = 8


logger.debug("Creating chihiro.rarity_text...")

db.cachedb.execute(""" DROP TABLE IF EXISTS rarity_text """)
db.cachedb.execute("""
    CREATE TABLE IF NOT EXISTS rarity_text (
        "id" INTEGER UNIQUE PRIMARY KEY,
        "text" TEXT UNIQUE
    )
""")
for rarity in Rarity:
    db.cachedb.execute("""
        INSERT OR IGNORE INTO rarity_text ("id", "text")
        VALUES (?,?)
    """, [rarity.value, rarity.name.lower()])
db.cachedb.commit()

logger.debug("chihiro.rarity_text created.")

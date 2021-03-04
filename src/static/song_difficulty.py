from enum import Enum

import customlogger as logger
from db import db


class Difficulty(Enum):
    DEBUT = 1
    REGULAR = 2
    PRO = 3
    MASTER = 4
    MPLUS = 5
    LEGACY = 101
    SMART = 11
    TRICK = 12
    PIANO = 21
    FORTE = 22

FLICK_DRAIN = {
    Difficulty.SMART: 0,
    Difficulty.TRICK: 8,
    Difficulty.DEBUT: 0,
    Difficulty.REGULAR: 0,
    Difficulty.PRO: 8,
    Difficulty.MASTER: 10,
    Difficulty.MPLUS: 10,
    Difficulty.LEGACY: 10,
    Difficulty.PIANO: 10,
    Difficulty.FORTE: 10,
}

NONFLICK_DRAIN = {
    Difficulty.SMART: 10,
    Difficulty.TRICK: 15,
    Difficulty.DEBUT: 10,
    Difficulty.REGULAR: 12,
    Difficulty.PRO: 15,
    Difficulty.MASTER: 20,
    Difficulty.MPLUS: 20,
    Difficulty.LEGACY: 20,
    Difficulty.PIANO: 10,
    Difficulty.FORTE: 10,
}

logger.debug("Creating chihiro.difficulty_text...")

db.cachedb.execute(""" DROP TABLE IF EXISTS difficulty_text """)
db.cachedb.execute("""
    CREATE TABLE IF NOT EXISTS difficulty_text (
        "id" INTEGER UNIQUE PRIMARY KEY,
        "text" TEXT UNIQUE
    )
""")
for diff in Difficulty:
    db.cachedb.execute("""
        INSERT OR IGNORE INTO difficulty_text ("id", "text")
        VALUES (?,?)
    """, [diff.value, diff.name.replace("MPLUS", "Master+").capitalize()])
db.cachedb.commit()

logger.debug("chihiro.difficulty_text created.")

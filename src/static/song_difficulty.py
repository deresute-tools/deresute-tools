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
    LIGHT = 11
    TRICK = 12
    PIANO = 21
    FORTE = 22

FLICK_DRAIN = {
    Difficulty.LIGHT: 0,
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
    Difficulty.LIGHT: 10,
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

GREAT_TAP_RANGE = {
    Difficulty.LIGHT: 120000,
    Difficulty.TRICK: 90000,
    Difficulty.DEBUT: 120000,
    Difficulty.REGULAR: 120000,
    Difficulty.PRO: 90000,
    Difficulty.MASTER: 80000,
    Difficulty.MPLUS: 80000,
    Difficulty.LEGACY: 80000,
    Difficulty.PIANO: 80000,
    Difficulty.FORTE: 80000,
}

PERFECT_TAP_RANGE = {
    Difficulty.LIGHT: 80000,
    Difficulty.TRICK: 70000,
    Difficulty.DEBUT: 80000,
    Difficulty.REGULAR: 80000,
    Difficulty.PRO: 70000,
    Difficulty.MASTER: 60000,
    Difficulty.MPLUS: 60000,
    Difficulty.LEGACY: 60000,
    Difficulty.PIANO: 60000,
    Difficulty.FORTE: 60000,
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

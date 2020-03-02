from enum import Enum

from src import customlogger as logger
from src.db import db


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

from enum import Enum

import customlogger as logger
from db import db


class Color(Enum):
    CUTE = 0
    COOL = 1
    PASSION = 2
    ALL = 3


logger.debug("Creating chihiro.color_text...")

db.cachedb.execute(""" DROP TABLE IF EXISTS color_text """)
db.cachedb.execute("""
    CREATE TABLE IF NOT EXISTS color_text (
        "id" INTEGER UNIQUE PRIMARY KEY,
        "text" TEXT UNIQUE
    )
""")
for color in Color:
    db.cachedb.execute("""
        INSERT OR IGNORE INTO color_text ("id", "text")
        VALUES (?,?)
    """, [color.value + 1, color.name.capitalize()])
db.cachedb.commit()

logger.debug("chihiro.color_text created.")

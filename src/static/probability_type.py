import customlogger as logger
from db import db



PROBABILITY_BASE = {1: ("Very Low", "vl"),
                    2: ("Low", "lo"),
                    3: ("Medium", "med"),
                    4: ("High", "hi"),
                    5: ("Very High", "vh")}

logger.debug("Creating chihiro.probability_keywords...")

db.cachedb.execute(""" DROP TABLE IF EXISTS probability_keywords """)
db.cachedb.execute("""
    CREATE TABLE IF NOT EXISTS probability_keywords (
        "id" INTEGER UNIQUE PRIMARY KEY,
        "keywords" TEXT UNIQUE,
        "short" TEXT UNIQUE 
    )
""")
for prob_id, (prob_name, prob_key) in PROBABILITY_BASE.items():
    db.cachedb.execute("""
        INSERT OR IGNORE INTO probability_keywords ("id", "keywords", "short")
        VALUES (?,?,?)
    """, [prob_id, prob_name, prob_key])
db.cachedb.commit()

logger.debug("chihiro.probability_keywords created.")

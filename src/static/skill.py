from src import customlogger as logger
from src.db import db

SKILL_BASE = {
    1: {"id": 1, "name": "SCORE Bonus", "keywords": ["su"]},
    2: {"id": 2, "name": "SCORE Bonus", "keywords": ["su"]},
    4: {"id": 4, "name": "COMBO Bonus", "keywords": ["cu"]},
    5: {"id": 5, "name": "PERFECT Support"},
    6: {"id": 6, "name": "PERFECT Support"},
    7: {"id": 7, "name": "PERFECT Support"},
    9: {"id": 9, "name": "COMBO Support"},
    12: {"id": 12, "name": "Damage Guard"},
    14: {"id": 14, "name": "Overload", "keywords": ["ol"]},
    15: {"id": 15, "name": "Concentration", "keywords": ["cc"]},
    16: {"id": 16, "name": "Encore"},
    17: {"id": 17, "name": "Life Recovery", "keywords": ["healer"]},
    20: {"id": 20, "name": "Skill Boost", "keywords": ["sb"]},
    21: {"id": 21, "name": "Cute Focus", "keywords": ["focus"]},
    22: {"id": 22, "name": "Cool Focus", "keywords": ["focus"]},
    23: {"id": 23, "name": "Passion Focus", "keywords": ["focus"]},
    24: {"id": 24, "name": "All-round", "keywords": ["ar"]},
    25: {"id": 25, "name": "Life Sparkle", "keywords": ["ls"]},
    26: {"id": 26, "name": "Tricolor Synergy"},
    27: {"id": 27, "name": "Coordinate"},
    28: {"id": 28, "name": "Long Act"},
    29: {"id": 29, "name": "Flick Act"},
    30: {"id": 30, "name": "Slide Act"},
    31: {"id": 31, "name": "Tuning"},
    32: {"id": 32, "name": "Cute Ensemble"},
    33: {"id": 33, "name": "Cool Ensemble"},
    34: {"id": 34, "name": "Passion Ensemble"},
    35: {"id": 35, "name": "Vocal Motif"},
    36: {"id": 36, "name": "Dance Motif"},
    37: {"id": 37, "name": "Visual Motif"},
    38: {"id": 38, "name": "Tricolor Symphony"},
    39: {"id": 39, "name": "Alternate"},
}

logger.debug("Creating chihiro.skill_keywords...")

db.cachedb.execute(""" DROP TABLE IF EXISTS skill_keywords """)
db.cachedb.execute("""
    CREATE TABLE IF NOT EXISTS skill_keywords (
        "id" INTEGER UNIQUE PRIMARY KEY,
        "skill_name" TEXT,
        "keywords" TEXT
    )
""")
for skill_id, skill_data in SKILL_BASE.items():
    db.cachedb.execute("""
        INSERT OR IGNORE INTO skill_keywords ("id", "skill_name", "keywords")
        VALUES (?,?,?)
    """, [skill_id,
          skill_data['name'],
          skill_data['name'] + " " + " ".join(skill_data['keywords'])
                                 if 'keywords' in skill_data
                                 else skill_data['name']])
db.cachedb.commit()

logger.debug("chihiro.skill_keywords created.")

SPARKLE_BONUS_SSR = {idx: _[0] for idx, _ in
                     enumerate(db.masterdb.execute_and_fetchall("SELECT type_01_value FROM skill_life_value"))}
SPARKLE_BONUS_SR = {idx: _[0] for idx, _ in
                    enumerate(db.masterdb.execute_and_fetchall("SELECT type_02_value FROM skill_life_value"))}
SPARKLE_BONUS_SSR_GRAND = {idx: _[0] for idx, _ in enumerate(
    db.masterdb.execute_and_fetchall("SELECT type_01_value FROM skill_life_value_grand"))}
SPARKLE_BONUS_SR_GRAND = {idx: _[0] for idx, _ in enumerate(
    db.masterdb.execute_and_fetchall("SELECT type_02_value FROM skill_life_value_grand"))}


def get_sparkle_bonus(rarity, grand=False):
    if grand:
        if rarity > 6:
            return SPARKLE_BONUS_SSR_GRAND
        if rarity > 4:
            return SPARKLE_BONUS_SR_GRAND
    else:
        if rarity > 6:
            return SPARKLE_BONUS_SSR
        if rarity > 4:
            return SPARKLE_BONUS_SR

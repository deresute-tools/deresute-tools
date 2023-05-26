from collections import OrderedDict

import customlogger as logger
from db import db

SKILL_BASE = {
    1: {"id": 1, "name": "SCORE Bonus", "keywords": ["su"], "color": (227, 98, 91)},
    2: {"id": 2, "name": "SCORE Bonus", "keywords": ["su"], "color": (227, 98, 91)},
    4: {"id": 4, "name": "COMBO Bonus", "keywords": ["cu"], "color": (255, 222, 0)},
    5: {"id": 5, "name": "PERFECT Support", "color": (52, 201, 119)},
    6: {"id": 6, "name": "PERFECT Support", "color": (52, 201, 119)},
    7: {"id": 7, "name": "PERFECT Support", "color": (52, 201, 119)},
    9: {"id": 9, "name": "COMBO Support", "color": (235, 199, 141)},
    12: {"id": 12, "name": "Damage Guard", "keywords": ["dg"], "color": (33, 133, 255)},
    14: {"id": 14, "name": "Overload", "keywords": ["ol"], "color": (212, 56, 255)},
    15: {"id": 15, "name": "Concentration", "keywords": ["cc"], "color": (104, 33, 181)},
    16: {"id": 16, "name": "Encore", "color": (48, 175, 186)},
    17: {"id": 17, "name": "Life Recovery", "keywords": ["healer"], "color": (47, 255, 36)},
    20: {"id": 20, "name": "Skill Boost", "keywords": ["sb"], "color": (227, 34, 227)},
    21: {"id": 21, "name": "Cute Focus", "keywords": ["focus"], "color": (252, 5, 141)},
    22: {"id": 22, "name": "Cool Focus", "keywords": ["focus"], "color": (55, 130, 191)},
    23: {"id": 23, "name": "Passion Focus", "keywords": ["focus"], "color": (227, 133, 18)},
    24: {"id": 24, "name": "All-round", "keywords": ["ar"], "color": (77, 150, 35)},
    25: {"id": 25, "name": "Life Sparkle", "keywords": ["ls"], "color": (250, 167, 77)},
    26: {"id": 26, "name": "Tricolor Synergy", "keywords": ["syn"], "color": (252, 98, 170)},
    27: {"id": 27, "name": "Coordinate", "color": (130, 56, 0)},
    28: {"id": 28, "name": "Long Act", "color": (209, 182, 151)},
    29: {"id": 29, "name": "Flick Act", "color": (147, 175, 201)},
    30: {"id": 30, "name": "Slide Act", "color": (177, 141, 196)},
    31: {"id": 31, "name": "Tuning", "color": (245, 189, 125)},
    32: {"id": 32, "name": "Cute Ensemble", "keywords": ["ens"], "color": (204, 63, 113)},
    33: {"id": 33, "name": "Cool Ensemble", "keywords": ["ens"], "color": (63, 63, 204)},
    34: {"id": 34, "name": "Passion Ensemble", "keywords": ["ens"], "color": (204, 162, 65)},
    35: {"id": 35, "name": "Vocal Motif", "color": (255, 94, 94)},
    36: {"id": 36, "name": "Dance Motif", "color": (0, 201, 212)},
    37: {"id": 37, "name": "Visual Motif", "color": (255, 178, 84)},
    38: {"id": 38, "name": "Tricolor Symphony", "keywords": ["sym"], "color": (255, 0, 238)},
    39: {"id": 39, "name": "Alternate", "keywords": ["alt"], "color": (158, 158, 158)},
    40: {"id": 40, "name": "Refrain", "keywords": ["ref"], "color": (100, 26, 20)},
    41: {"id": 41, "name": "Magic", "keywords": ["mag"], "color": (185, 242, 136)},
    42: {"id": 42, "name": "Mutual", "color": (58, 58, 58)},
    43: {"id": 43, "name": "Overdrive", "keywords": ["od"], "color": (106, 28, 127)},
}

SKILL_COLOR_BY_NAME = {
    v['name']: v['color'] for v in SKILL_BASE.values()
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

SPARKLE_BONUS_SSR = OrderedDict({_[0]: _[1] for idx, _ in
                     enumerate(db.masterdb.execute_and_fetchall("SELECT life_value / 10, type_01_value FROM skill_life_value ORDER BY life_value"))})
SPARKLE_BONUS_SR = OrderedDict({_[0]: _[1] for idx, _ in
                    enumerate(db.masterdb.execute_and_fetchall("SELECT life_value / 10, type_02_value FROM skill_life_value ORDER BY life_value"))})
SPARKLE_BONUS_SSR_GRAND = OrderedDict({_[0]: _[1] for idx, _ in enumerate(
    db.masterdb.execute_and_fetchall("SELECT life_value / 10, type_01_value FROM skill_life_value_grand ORDER BY life_value"))})
SPARKLE_BONUS_SR_GRAND = OrderedDict({_[0]: _[1] for idx, _ in enumerate(
    db.masterdb.execute_and_fetchall("SELECT life_value / 10, type_02_value FROM skill_life_value_grand ORDER BY life_value"))})

for d in [SPARKLE_BONUS_SSR, SPARKLE_BONUS_SR, SPARKLE_BONUS_SSR_GRAND, SPARKLE_BONUS_SR_GRAND]:
    c_v = 0
    for key, value in d.items():
        if value < c_v:
            d[key] = c_v
        if c_v < value:
            c_v = value

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

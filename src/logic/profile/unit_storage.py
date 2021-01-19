from db import db


def initialize_personal_units():
    db.cachedb.execute("DROP TABLE IF EXISTS personal_units")
    db.cachedb.execute("""
    CREATE TABLE personal_units (
        unit_name TEXT PRIMARY KEY UNIQUE CHECK(unit_name <> ''),
        grand INTEGER,
        cards BLOB 
        )
    """)
    db.cachedb.commit()


def update_unit(unit_name, cards, grand=False):
    if isinstance(cards, list):
        cards = ["" if _ is None else str(_) for _ in cards]
        cards = ",".join(cards)
    db.cachedb.execute("INSERT OR REPLACE INTO personal_units (unit_name, grand, cards) VALUES (?,?,?)",
                       [unit_name, grand, cards])
    db.cachedb.commit()


def delete_unit(unit_name):
    db.cachedb.execute("DELETE FROM personal_units WHERE unit_name = ? ", [unit_name])
    db.cachedb.commit()


def clean_all_units(grand=False):
    grand = 1 if grand else 0
    db.cachedb.execute("DELETE FROM personal_units WHERE grand = ? ", [grand])
    db.cachedb.commit()

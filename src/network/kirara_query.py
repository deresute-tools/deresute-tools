import json

import requests

from db import db


def _base_query(query):
    query_url = "https://starlight.kirara.ca/api/v1/{}".format(query)
    response = requests.get(query_url)
    return json.loads(response.content)


def get_truth_version():
    return _base_query("info")['truth_version']


def update_chara_data():
    chara_data = _base_query("list/char_t")['result']
    db.cachedb.execute("""
        CREATE TABLE IF NOT EXISTS chara_cache (
        "conventional" TEXT UNIQUE,
        "chara_id" INTEGER UNIQUE PRIMARY KEY,
        "full_name" TEXT
        )
    """)
    for data in chara_data:
        db.cachedb.execute("""
            INSERT OR IGNORE INTO chara_cache ("conventional","chara_id", "full_name")
            VALUES (?,?,?)
        """, [
            data['conventional'].split()[-1].lower(),
            data['chara_id'],
            data['conventional']
        ])
    db.cachedb.commit()


if __name__ == '__main__':
    update_chara_data()

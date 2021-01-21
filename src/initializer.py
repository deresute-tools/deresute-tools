"""
Import all modules in the correct order
"""
from settings import MANIFEST_PATH, MASTERDB_PATH
from utils import storage


def load_static():
    from static import color, leader, probability_type, rarity, skill, song_difficulty

    assert color
    assert leader
    assert probability_type
    assert rarity
    assert skill
    assert song_difficulty


def setup(update=False):
    load_static()
    if not (storage.exists(MANIFEST_PATH) and storage.exists(MASTERDB_PATH)):
        update = True
    from db import db
    assert db
    from network import meta_updater
    if update:
        meta_updater.update_database()
    from network import music_updater
    music_updater.update_musicscores()
    from network import chart_cache_updater
    chart_cache_updater.update_cache_scores()
    from logic.search import card_query
    assert card_query
    from network import image_updater
    assert image_updater
    from logic.profile import profile_manager
    assert profile_manager
    from logic.search import indexer, search_engine
    assert indexer
    assert search_engine


if __name__ == '__main__':
    setup(False)

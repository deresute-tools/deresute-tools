"""
Import all modules in the correct order
"""
from settings import MANIFEST_PATH, MASTERDB_PATH
from utils import storage


def setup(update=False):
    if not (storage.exists(MANIFEST_PATH) and storage.exists(MASTERDB_PATH)):
        update = True
    from src.db import db
    assert db
    from src.network import meta_updater
    if update:
        meta_updater.update_database()
    from src.network import music_updater
    music_updater.update_musicscores()
    from src.logic.search import card_query
    assert card_query
    from src.network import image_updater
    assert image_updater
    from src.logic.profile import profile_manager
    assert profile_manager
    from src.logic.search import indexer, search_engine
    assert indexer
    assert search_engine


if __name__ == '__main__':
    setup(False)

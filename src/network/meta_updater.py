import logging
import sqlite3

import customlogger as logger
from network import cgss_query
from settings import *
from utils import storage
from utils.misc import decompress


def _update_manifest():
    logger.debug("Updating manifest.db")
    manifest_response = cgss_query.get_manifests()

    with storage.get_writer(MANIFEST_PATH, 'wb') as fwb:
        fwb.write(decompress(manifest_response.content))
    logger.info("manifest.db updated")


def _update_masterdb():
    logger.debug("Updating master.db")
    manifest_conn = sqlite3.connect(get_manifestdb_path())
    manifest_c = manifest_conn.cursor()

    manifest_c.execute('SELECT hash FROM manifests WHERE name="master.mdb"')
    master_hash = manifest_c.fetchone()[0]
    master_response = cgss_query.get_db(master_hash)

    with storage.get_writer(MASTERDB_PATH, 'wb') as fwb:
        fwb.write(decompress(master_response.content))
    manifest_c.close()
    manifest_conn.close()
    logger.info("master.db updated")


def get_manifestdb_path():
    if not storage.exists(MANIFEST_PATH):
        logger.debug("manifest.db not found, triggering manifest updater")
        _update_manifest()
    return MANIFEST_PATH


def get_masterdb_path():
    if not storage.exists(MASTERDB_PATH):
        logger.debug("master.db not found, triggering manifest updater")
        _update_masterdb()
    return MASTERDB_PATH


def get_cachedb_path():
    if not storage.exists(CACHEDB_PATH):
        conn = sqlite3.connect(CACHEDB_PATH)
        conn.close()
    return CACHEDB_PATH


def update_database():
    _update_manifest()
    _update_masterdb()


if __name__ == '__main__':
    logging.basicConfig(level=logging.CRITICAL,
                        format='%(asctime)s - %(levelname)s - %(module)s - %(message)s',
                        datefmt='%d-%b-%y %H:%M:%S')
    logger.setLevel(logging.DEBUG)
    update_database()

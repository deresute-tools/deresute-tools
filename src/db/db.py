import sqlite3
from collections import OrderedDict

from network import meta_updater


class CustomDB(object):

    def __init__(self, path):
        self._db_connection = sqlite3.connect(path)
        self._db_cur = self._db_connection.cursor()

    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        self._db_connection.rollback()
        self._db_cur.close()
        self._db_connection.close()

    def execute_and_fetchone(self, query, params=None, out_dict=False):
        self.execute(query, params)
        result = self._db_cur.fetchone()
        if out_dict:
            description = self._db_cur.description
            return OrderedDict({key[0]: value for key, value in zip(description, result)})
        else:
            return result

    def execute_and_fetchall(self, query, params=None, out_dict=False):
        self.execute(query, params)
        result = self._db_cur.fetchall()
        if out_dict:
            description = self._db_cur.description
            return [OrderedDict({key[0]: value for key, value in zip(description, _)}) for _ in result]
        else:
            return result

    def execute(self, query, params=None):
        if params is None:
            self._db_cur.execute(query)
        else:
            self._db_cur.execute(query, params)

    def commit(self):
        self._db_connection.commit()

    def get_connection(self):
        return self._db_connection


masterdb = CustomDB(meta_updater.get_masterdb_path())
cachedb = CustomDB(meta_updater.get_cachedb_path())

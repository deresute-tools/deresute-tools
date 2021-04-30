from whoosh import scoring
from whoosh.qparser import QueryParser

import customlogger as logger
from logic.search import indexer


class BaseSearchEngine:
    _searcher = None
    _ix = None

    def execute_query(self, query_str, limit=None):
        query = QueryParser("content", self._ix.schema).parse(query_str)
        results = self._searcher.search(query, limit=limit)
        logger.debug("Query '{}' took {} to run.".format(query_str, results.runtime))
        return results


class SearchEngine(BaseSearchEngine):

    def __init__(self):
        self.refresh_searcher()

    def refresh_searcher(self):
        self._ix = indexer.im.get_index()
        self._searcher = self._ix.searcher(weighting=scoring.TF_IDF())


class SongSearchEngine(BaseSearchEngine):

    def __init__(self):
        self._ix = indexer.im.get_index(song_index=True)
        self._searcher = self._ix.searcher(weighting=scoring.TF_IDF())


def advanced_single_query(query, partial_match=True, idolized=True, ssr=True, owned_only=False):
    query = query.split()
    if partial_match:
        for idx in range(len(query)):
            if query[idx] == "OR" or query[idx] == "AND":
                continue
            if query[idx][-1] == "+":
                continue
            query[idx] += "*"
    query = " ".join(query)
    if idolized:
        query = query + " idolized:true"
    if ssr:
        query = query + " rarity:ssr*"
    if owned_only:
        query = query + " owned:[1 TO]"
    results = engine.execute_query(query)
    if len(results) >= 1:
        return [int(_['title']) for _ in results]
    return []


def song_query(query, partial_match=True):
    query = query.split()
    if partial_match:
        for idx in range(len(query)):
            query[idx] += "*"
    query = " ".join(query)
    results = song_engine.execute_query(query)
    if len(results) >= 1:
        return [int(_['title']) for _ in results]
    return []


engine = SearchEngine()
song_engine = SongSearchEngine()

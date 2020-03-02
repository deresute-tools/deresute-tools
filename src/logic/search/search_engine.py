from whoosh import scoring
from whoosh.qparser import QueryParser

from logic.search import indexer
from src import customlogger as logger


class SearchEngine:

    def __init__(self):
        self._ix = indexer.im.get_index()
        self._searcher = self._ix.searcher(weighting=scoring.TF_IDF())

    def execute_query(self, query_str, limit=None):
        query = QueryParser("content", self._ix.schema).parse(query_str)
        results = self._searcher.search(query, limit=limit)
        logger.debug("Query '{}' took {} to run.".format(query_str, results.runtime))
        return results


def advanced_single_query(query, partial_match=True, idolized=True, ssr=True, owned_only=False):
    query = query.split()
    if partial_match:
        for idx in range(len(query)):
            if query[idx] == "OR" or query[idx] == "AND":
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


engine = SearchEngine()

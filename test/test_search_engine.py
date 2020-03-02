import unittest

from src.logic.search import card_query
from src.logic.search.search_engine import engine


class TestSearchEngine(unittest.TestCase):
    def test_search(self):
        self.assertEqual(engine.execute_query("uzuki2 ssr")[0]['title'], '100256')
        self.assertEqual(engine.execute_query("uzuki ssru tricolor")[0]['title'], '100255')
        self.assertEqual(int(engine.execute_query("uzuki focus")[0]['title']),
                         card_query.convert_short_name_to_id('uzuki3u')[0])
        self.assertEqual(int(engine.execute_query("uzuki ssr princess")[0]['title']),
                         card_query.convert_short_name_to_id('uzuki3')[0])
        self.assertEqual(int(engine.execute_query("uzuki coord*")[1]['title']),
                         card_query.convert_short_name_to_id('uzuki4')[0])
        self.assertEqual(int(engine.execute_query("chara:uzuki* skill:coord* idolized:false")[0]['title']),
                         card_query.convert_short_name_to_id('uzuki4u')[0])

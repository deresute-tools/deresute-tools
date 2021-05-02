import unittest

from logic.search import card_query
from logic.search.search_engine import engine, song_engine


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

    def test_song_search(self):
        self.assertEqual(song_engine.execute_query("message")[0]['title'], '89')
        self.assertEqual(song_engine.execute_query("shiki solo")[0]['title'], '401')
        self.assertEqual(song_engine.execute_query("shiki solo")[1]['title'], '402')
        self.assertEqual(song_engine.execute_query("shiki solo")[2]['title'], '403')
        self.assertEqual(song_engine.execute_query("shiki solo")[3]['title'], '404')
        self.assertEqual(song_engine.execute_query("us")[0]['title'], '2550')

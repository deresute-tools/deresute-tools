import unittest

from src.logic.search.card_query import convert_short_name_to_id
from src.logic.search.search_engine import advanced_single_query


class TestQueryCard(unittest.TestCase):
    def test_short_name_to_id(self):
        self.assertListEqual(convert_short_name_to_id("kaeder1"), [200024])
        self.assertListEqual(convert_short_name_to_id("rinsr3"), [200492])
        self.assertListEqual(convert_short_name_to_id("uzuki1"), [100076])
        self.assertListEqual(convert_short_name_to_id("uzuki3"), [100448])
        self.assertListEqual(convert_short_name_to_id("kaede2"), [200294])
        self.assertListEqual(convert_short_name_to_id("rika4u"), [300761])
        self.assertListEqual(convert_short_name_to_id("rin2"), [200254])
        self.assertListEqual(convert_short_name_to_id("sae4"), [100746])
        self.assertListEqual(convert_short_name_to_id("kyoko4 uzuki1 kanako1 uzuki3 anzu4 kyoko4"),
                             [100762, 100076, 100098, 100448, 100652, 100762])

    def test_advanced_query(self):
        self.assertListEqual(advanced_single_query("uzu prin", idolized=False), [100447, 100448])
        self.assertListEqual(advanced_single_query("kae trico"), [200294])
        self.assertListEqual(advanced_single_query("karin1 overl idolized:true"), [100398])
        self.assertListEqual(advanced_single_query("karin1 overl idolized:true", partial_match=False), [])

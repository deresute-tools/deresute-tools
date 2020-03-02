import unittest

from src.db import db
from logic.profile import potential
from logic.profile.profile_manager import pm


class TestProfile(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pm.add_profile('unit_test')

    @classmethod
    def tearDownClass(cls):
        pm.delete_profile('unit_test')

    def test_update_potential(self):
        a_ar = [0, 40, 80, 120, 170, 220, 270, 320, 380, 440, 500]
        l_ar = [0, 1, 2, 4, 6, 8, 10, 13, 16, 19, 22]
        s_ar = [0, 100, 200, 300, 400, 600, 800, 1000, 1300, 1600, 2000]
        for idx in range(11):
            potential.update_potential(101, (idx, idx, idx, idx, idx))
            d = db.cachedb.execute_and_fetchone(
                "SELECT bonus_vocal,bonus_visual,bonus_dance,bonus_hp,bonus_skill FROM card_data_cache WHERE chara_id = 101 AND rarity = 8")
            self.assertEqual(212 + a_ar[idx], d[0])
            self.assertEqual(209 + a_ar[idx], d[1])
            self.assertEqual(209 + a_ar[idx], d[2])
            self.assertEqual(2 + l_ar[idx], d[3])
            self.assertEqual(s_ar[idx], d[4])

import unittest

from src.logic.skill import Skill


class TestSkill(unittest.TestCase):
    def test_score_bonus(self):
        su_4s_hi = Skill.from_id(300327)
        self.assertEqual(su_4s_hi.v0, 117)
        self.assertEqual(su_4s_hi.v1, 0)
        self.assertEqual(su_4s_hi.v2, 0)
        self.assertEqual(su_4s_hi.duration, 3)
        self.assertEqual(su_4s_hi.interval, 4)
        self.assertEqual(su_4s_hi.probability, 8000)

    def test_combo_bonus(self):
        cu_7s_me = Skill.from_id(200117)
        self.assertEqual(cu_7s_me.v0, 0)
        self.assertEqual(cu_7s_me.v1, 118)
        self.assertEqual(cu_7s_me.v2, 0)
        self.assertEqual(cu_7s_me.duration, 6)
        self.assertEqual(cu_7s_me.interval, 7)
        self.assertEqual(cu_7s_me.probability, 7250)

    def test_skill_boost(self):
        sb_10s_hi = Skill.from_id(100479)
        self.assertEqual(sb_10s_hi.v0, 1200)
        self.assertEqual(sb_10s_hi.v1, 1200)
        self.assertEqual(sb_10s_hi.v2, 1200)
        self.assertEqual(sb_10s_hi.duration, 9)
        self.assertEqual(sb_10s_hi.interval, 10)
        self.assertEqual(sb_10s_hi.probability, 8000)
        assert sb_10s_hi.boost

    def test_SYN(self):
        syn_11s_hi = Skill.from_id(200525, 5)
        self.assertEqual(syn_11s_hi.v0, 116)
        self.assertEqual(syn_11s_hi.v1, 115)
        self.assertEqual(syn_11s_hi.v2, 1)
        self.assertEqual(syn_11s_hi.duration, 7.5)
        self.assertEqual(syn_11s_hi.interval, 11)

    def test_ENS(self):
        ens_9s_hi = Skill.from_id(100761)
        self.assertEqual(ens_9s_hi.v0, 1500)
        self.assertEqual(ens_9s_hi.v1, 1500)
        self.assertEqual(ens_9s_hi.v2, 1000)
        self.assertEqual(ens_9s_hi.duration, 6)
        self.assertEqual(ens_9s_hi.interval, 9)
        self.assertEqual(ens_9s_hi.probability, 8000)
        assert ens_9s_hi.boost

    def test_SYM(self):
        sym_9s_hi = Skill.from_id(300761)
        self.assertEqual(sym_9s_hi.v0, 1500)
        self.assertEqual(sym_9s_hi.v1, 1500)
        self.assertEqual(sym_9s_hi.v2, 1200)
        self.assertEqual(sym_9s_hi.duration, 6)
        self.assertEqual(sym_9s_hi.interval, 9)
        self.assertEqual(sym_9s_hi.probability, 8000)
        assert sym_9s_hi.boost

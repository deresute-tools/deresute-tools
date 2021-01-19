import unittest

import numpy as np

from logic.leader import Leader


class TestLeader(unittest.TestCase):
    def test_cute_voice(self):
        cu_vo = Leader.from_id(1)
        np.testing.assert_equal(cu_vo.bonuses, np.array([
            [30, 0, 0, 0, 0],
            [0, 0, 0, 0, 0],
            [0, 0, 0, 0, 0],
        ]).transpose().astype(float))
        self.assertFalse(cu_vo.resonance)
        self.assertFalse(cu_vo.unison)

    def test_passion_step(self):
        pa_da = Leader.from_id(12)
        np.testing.assert_equal(pa_da.bonuses, np.array([
            [0, 0, 0, 0, 0],
            [0, 0, 0, 0, 0],
            [0, 0, 30, 0, 0],
        ]).transpose().astype(float))
        self.assertFalse(pa_da.resonance)
        self.assertFalse(pa_da.unison)

    def test_cool_energy(self):
        co_lf = Leader.from_id(56)
        np.testing.assert_equal(co_lf.bonuses, np.array([
            [0, 0, 0, 0, 0],
            [0, 0, 0, 30, 0],
            [0, 0, 0, 0, 0],
        ]).transpose().astype(float))
        self.assertFalse(co_lf.resonance)
        self.assertFalse(co_lf.unison)

    def test_cool_ability(self):
        co_sk = Leader.from_id(68)
        np.testing.assert_equal(co_sk.bonuses, np.array([
            [0, 0, 0, 0, 0],
            [0, 0, 0, 0, 40],
            [0, 0, 0, 0, 0],
        ]).transpose().astype(float))
        self.assertFalse(co_sk.resonance)
        self.assertFalse(co_sk.unison)

    def test_tri_make(self):
        tri_vi = Leader.from_id(72)
        np.testing.assert_equal(tri_vi.bonuses, np.array([
            [0, 100, 0, 0, 0],
            [0, 100, 0, 0, 0],
            [0, 100, 0, 0, 0],
        ]).transpose().astype(float))
        np.testing.assert_equal(tri_vi.min_requirements, np.array([1, 1, 1]))
        self.assertFalse(tri_vi.resonance)
        self.assertFalse(tri_vi.unison)

    def test_pa_princess(self):
        pa_pr = Leader.from_id(76)
        np.testing.assert_equal(pa_pr.bonuses, np.array([
            [0, 0, 0, 0, 0],
            [0, 0, 0, 0, 0],
            [50, 50, 50, 0, 0],
        ]).transpose().astype(float))
        np.testing.assert_equal(pa_pr.max_requirements, np.array([0, 0, 99]))
        self.assertFalse(pa_pr.resonance)
        self.assertFalse(pa_pr.unison)

    def test_cox_cu(self):
        co_cu = Leader.from_id(109)
        np.testing.assert_equal(co_cu.bonuses, np.array([
            [20, 20, 20, 0, 25],
            [20, 20, 20, 0, 25],
            [20, 20, 20, 0, 25],
        ]).transpose().astype(float))
        np.testing.assert_equal(co_cu.min_requirements, np.array([1, 1, 0]))
        self.assertFalse(co_cu.resonance)
        self.assertFalse(co_cu.unison)

    def test_reso_voice(self):
        re_vo = Leader.from_id(104)
        np.testing.assert_equal(re_vo.bonuses, np.array([
            [0, -100, -100, 0, 0],
            [0, -100, -100, 0, 0],
            [0, -100, -100, 0, 0],
        ]).transpose().astype(float))
        np.testing.assert_equal(re_vo.min_requirements, np.array([0, 0, 0]))
        self.assertTrue(re_vo.resonance)
        self.assertFalse(re_vo.unison)

    def test_cool_unison(self):
        co_un = Leader.from_id(102)
        np.testing.assert_equal(co_un.bonuses, np.array([
            [0, 0, 0, 0, 0],
            [30, 30, 30, 0, 0],
            [0, 0, 0, 0, 0],
        ]).transpose().astype(float))
        np.testing.assert_equal(co_un.min_requirements, np.array([0, 0, 0]))
        self.assertFalse(co_un.resonance)
        self.assertTrue(co_un.unison)
        np.testing.assert_equal(co_un.song_bonuses, np.array([
            [0, 0, 0, 0, 0],
            [55, 55, 55, 0, 0],
            [0, 0, 0, 0, 0],
        ]).transpose().astype(float))

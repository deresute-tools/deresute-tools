import numpy as np

from db import db


class Leader:
    def __init__(self, bonuses=np.zeros((5, 3)), song_bonuses=None, min_requirements=None, max_requirements=None,
                 resonance=False, unison=False, bless=False):
        assert isinstance(bonuses, np.ndarray)
        assert bonuses.shape == (5, 3)
        if min_requirements is not None:
            assert len(min_requirements) == 3
        else:
            min_requirements = np.array([0, 0, 0])
        if max_requirements is not None:
            assert len(max_requirements) == 3
        else:
            max_requirements = np.array([99, 99, 99])
        #  5 params x 3 colors
        # Params in order: Vo Vi Da Lf Sk
        self.bonuses = bonuses
        self.song_bonuses = song_bonuses
        self.resonance = resonance
        self.bless = bless
        self.min_requirements = min_requirements
        self.max_requirements = max_requirements
        self.unison = unison

    @classmethod
    def from_id(cls, leader_id):
        if leader_id == 0:
            return cls()  # Default leader with 0 bonus
        leader_data = db.masterdb.execute_and_fetchone(
            """
            SELECT leader_skill_data.*
            FROM leader_skill_data
            WHERE id = ?
            """,
            params=[leader_id],
            out_dict=True)

        bonuses = np.zeros((5, 3))
        for i in range(2):
            target_attribute_key = "target_attribute_2" if i == 1 else "target_attribute"
            target_param_key = "target_param_2" if i == 1 else "target_param"
            up_value_key = "up_value_2" if i == 1 else "up_value"
            if leader_data[target_attribute_key] == 4:
                # All colors
                if leader_data[target_param_key] == 4:
                    bonuses[0:3, :] += leader_data[up_value_key]
                elif 0 < leader_data[target_param_key] < 4:
                    bonuses[leader_data[target_param_key] - 1, :] += leader_data[up_value_key]
                elif 4 < leader_data[target_param_key] < 7:
                    bonuses[leader_data[target_param_key] - 2, :] += leader_data[up_value_key]
            elif 0 < leader_data[target_attribute_key] < 4:
                # Single color
                if leader_data[target_param_key] == 4:
                    bonuses[0:3, leader_data[target_attribute_key] - 1] += leader_data[up_value_key]
                elif 0 < leader_data[target_param_key] < 4:
                    bonuses[leader_data[target_param_key] - 1, leader_data[target_attribute_key] - 1] += leader_data[
                        up_value_key]
                elif 4 < leader_data[target_param_key] < 7:
                    bonuses[leader_data[target_param_key] - 2, leader_data[target_attribute_key] - 1] += leader_data[
                        up_value_key]
        is_unison = 10 < leader_data["target_attribute_2"] < 14
        if is_unison:
            song_bonuses = np.zeros((5, 3))
            song_bonuses[0:3, leader_data["target_attribute"] - 1] += leader_data["up_value_2"]
        else:
            song_bonuses = None

        is_bless = leader_data['type'] == 100

        is_reso = leader_data['type'] == 70
        if is_reso:
            bonuses[0:3, :] = -100
            bonuses[leader_data['param_limit'] - 1] = 0

        requirements = [leader_data["need_cute"], leader_data["need_cool"], leader_data["need_passion"]]
        min_requirements, max_requirements = None, None
        for idx, requirement in enumerate(requirements):
            if requirement == 6:
                max_requirements = np.array([0, 0, 0])
                max_requirements[idx] = 99
                min_requirements = np.array([0, 0, 0])
                break
        if min_requirements is None:
            min_requirements = requirements

        return cls(
            bonuses=bonuses,
            song_bonuses=song_bonuses,
            resonance=is_reso,
            min_requirements=min_requirements,
            max_requirements=max_requirements,
            unison=is_unison,
            bless=is_bless,
        )

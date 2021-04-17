from gui.events.utils.wrappers import BaseSimulationResultWithUuid


class GetAllCardsEvent:
    def __init__(self):
        pass


class SimulationEvent:
    def __init__(self, uuid, appeals, autoplay, autoplay_offset, doublelife, extra_bonus, extra_return,
                 hidden_feature_check,
                 live, mirror, perfect_play, results, special_option, special_value, support, times, unit):
        self.uuid = uuid
        self.appeals = appeals
        self.autoplay = autoplay
        self.autoplay_offset = autoplay_offset
        self.doublelife = doublelife
        self.extra_bonus = extra_bonus
        self.extra_return = extra_return
        self.hidden_feature_check = hidden_feature_check
        self.live = live
        self.mirror = mirror
        self.perfect_play = perfect_play
        self.results = results
        self.special_option = special_option
        self.special_value = special_value
        self.support = support
        self.times = times
        self.unit = unit


class DisplaySimulationResultEvent:
    def __init__(self, payload: BaseSimulationResultWithUuid):
        self.payload = payload


class AddEmptyUnitEvent:
    def __init__(self, active_tab):
        self.active_tab = active_tab


class YoinkUnitEvent:
    def __init__(self, live_detail_id):
        self.live_detail_id = live_detail_id


class SetSupportCardsEvent:
    def __init__(self, cards):
        self.cards = cards


class RequestSupportTeamEvent:
    def __init__(self):
        pass


class SupportTeamSetMusicEvent:
    def __init__(self, score_id, difficulty):
        self.score_id = score_id
        self.difficulty = difficulty

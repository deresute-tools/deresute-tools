from gui.events.utils.wrappers import BaseSimulationResultWithUuid


class GetAllCardsEvent:
    def __init__(self, model, row):
        self.model = model
        self.row = row


class SimulationEvent:
    def __init__(self, uuid, short_uuid, abuse_load, appeals, autoplay, autoplay_offset, doublelife, extra_bonus,
                 extra_return, hidden_feature_check, live, mirror, perfect_play, results, special_option, special_value,
                 support, times, unit, left_inclusive, right_inclusive):
        self.uuid = uuid
        self.short_uuid = short_uuid
        self.abuse_load = abuse_load
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
        self.left_inclusive = left_inclusive
        self.right_inclusive = right_inclusive


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


class PushCardEvent:
    def __init__(self, card_id, skip_guest_push=False):
        self.card_id = card_id
        self.skip_guest_push = skip_guest_push


class ContextAwarePushCardEvent:
    def __init__(self, model, event: PushCardEvent):
        self.model = model
        self.event = event

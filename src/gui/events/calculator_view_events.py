from gui.events.utils.wrappers import BaseSimulationResultWithUuid


class GetAllCardsEvent:
    def __init__(self, model, row):
        self.model = model
        self.row = row


class SimulationEvent:
    def __init__(self, uuid, short_uuid, abuse_load, appeals, autoplay, autoplay_offset, doublelife, extra_bonus,
                 extra_return, live, mirror, perfect_play, results, special_option, special_value,
                 support, times, unit, left_inclusive, right_inclusive, theoretical_simulation=False,
                 force_encore_amr_cache_to_encore_unit=False,
                 force_encore_magic_to_encore_unit=False,
                 allow_encore_magic_to_escape_max_agg=True,
                 allow_great=False
                 ):
        self.uuid = uuid
        self.short_uuid = short_uuid
        self.abuse_load = abuse_load
        self.appeals = appeals
        self.autoplay = autoplay
        self.autoplay_offset = autoplay_offset
        self.doublelife = doublelife
        self.extra_bonus = extra_bonus
        self.extra_return = extra_return
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
        self.theoretical_simulation = theoretical_simulation
        self.force_encore_amr_cache_to_encore_unit = force_encore_amr_cache_to_encore_unit
        self.force_encore_magic_to_encore_unit = force_encore_magic_to_encore_unit
        self.allow_encore_magic_to_escape_max_agg = allow_encore_magic_to_escape_max_agg
        self.allow_great = allow_great


class DisplaySimulationResultEvent:
    def __init__(self, payload: BaseSimulationResultWithUuid):
        self.payload = payload


class AddEmptyUnitEvent:
    def __init__(self, active_tab):
        self.active_tab = active_tab


class YoinkUnitEvent:
    def __init__(self, live_detail_id, rank, player_id):
        self.live_detail_id = live_detail_id
        self.rank = rank
        self.player_id = player_id


class SetSupportCardsEvent:
    def __init__(self, extended_cards_data):
        self.extended_cards_data = extended_cards_data


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


class TurnOffRunningLabelFromUuidEvent:
    def __init__(self, uuid):
        self.uuid = uuid


class ToggleUnitLockingOptionsVisibilityEvent:
    def __init__(self):
        pass

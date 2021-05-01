class HookUnitToChartViewerEvent:
    def __init__(self, cards):
        self.cards = cards


class HookAbuseToChartViewerEvent:
    def __init__(self, cards, score_array, perfect_score_array):
        self.cards = cards
        self.score_array = score_array
        self.perfect_score_array = perfect_score_array


class SendMusicEvent:
    def __init__(self, song_id, difficulty):
        self.song_id = song_id
        self.difficulty = difficulty


class ToggleMirrorEvent:
    def __init__(self, mirrored):
        self.mirrored = mirrored


class PopupChartViewerEvent:
    def __init__(self, look_for_chart=False):
        self.look_for_chart = look_for_chart

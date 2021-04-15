class HookUnitToChartViewerEvent:
    def __init__(self, cards):
        self.cards = cards


class HookAbuseToChartViewerEvent:
    def __init__(self, cards, score_matrix, perfect_score_array):
        self.cards = cards
        self.score_matrix = score_matrix
        self.perfect_score_array = perfect_score_array


class SendMusicEvent:
    def __init__(self, song_id, difficulty):
        self.song_id = song_id
        self.difficulty = difficulty


class ToggleMirrorEvent:
    def __init__(self, mirrored):
        self.mirrored = mirrored


class PopupChartViewerEvent:
    def __init__(self):
        pass

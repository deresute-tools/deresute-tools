class PushCardIndexEvent:
    def __init__(self, idx, skip_guest_push):
        self.idx = idx
        self.skip_guest_push = skip_guest_push

class ToggleQuickSearchOptionEvent:
    def __init__(self, option):
        self.option = option
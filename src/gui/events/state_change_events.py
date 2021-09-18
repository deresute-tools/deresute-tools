class AutoFlagChangeEvent:
    def __init__(self, flag):
        self.flag = flag


class PostYoinkEvent:
    def __init__(self, support):
        self.support = support


class PotentialUpdatedEvent:
    def __init__(self, card_list):
        self.card_list = card_list


class SetTipTextEvent:
    def __init__(self, text):
        self.text = text


class InjectTextEvent:
    def __init__(self, text, offset=10):
        self.text = text
        self.offset = offset


class ShutdownTriggeredEvent:
    def __init__(self):
        pass


class BackupFlagsEvent:
    def __init__(self):
        pass

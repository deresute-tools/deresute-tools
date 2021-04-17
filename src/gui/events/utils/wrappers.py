from simulator import BaseSimulationResult


class BaseSimulationResultWithUuid:
    def __init__(self, uuid, results: BaseSimulationResult, abuse_load):
        self.uuid = uuid
        self.results = results
        self.abuse_load = abuse_load


class YoinkResults:
    def __init__(self, cards, support):
        self.cards = cards
        self.support = support

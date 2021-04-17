from simulator import BaseSimulationResult


class BaseSimulationResultWithUuid:
    def __init__(self, uuid, results: BaseSimulationResult):
        self.uuid = uuid
        self.results = results


class YoinkResults:
    def __init__(self, cards, support):
        self.cards = cards
        self.support = support

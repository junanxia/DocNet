
from model import ModelClass
from parser.contract import ContractParser
from parser.blueprint import BlueprintParser
from parser.check import CheckParser
from parser.evaluate import EvaluateParser


class ParserWrapper(object):
    def __init__(self) -> None:
        self.model_class = ModelClass()

        self.contract_parser = ContractParser(self.model_class)
        self.blueprint_parser = BlueprintParser(self.model_class)
        self.check_parser = CheckParser(self.model_class)
        self.evaluate_parser = EvaluateParser(self.model_class)


parser_wrapper = ParserWrapper()

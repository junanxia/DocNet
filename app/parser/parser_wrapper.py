
from model import ModelClass
from parser.contract_parser import ContractParser
from parser.blueprint_parser import BlueprintParser


class ParserWrapper(object):
    def __init__(self) -> None:
        self.model_class = ModelClass()

        self.contract_parser = ContractParser(self.model_class)
        self.blueprint_parser = BlueprintParser(self.model_class)


parser_wrapper = ParserWrapper()

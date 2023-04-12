import abc
import json


class MetaPrompt(metaclass=abc.ABCMeta):
    def __init__(self, prompt_data: str):
        self.prompt_data = json.loads(prompt_data)

    def get_prompt(self) -> list:
        return [x for x in self.prompt_data]


class Prompt:
    pass

class Command(MetaPrompt):
    def __init__(self, prompt_data: str):
        super().__init__(prompt_data)
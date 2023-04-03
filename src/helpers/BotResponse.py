from typing import Union


class BotResponse:
    def __init__(self, full_response, response_str=None, new_mood=None, new_memory=None):
        self.full_response: str = full_response
        self.response_str: str = response_str
        self.new_mood: Union[None, str] = new_mood
        self.new_memory: Union[None, str] = new_memory



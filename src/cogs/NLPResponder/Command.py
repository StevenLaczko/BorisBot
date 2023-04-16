import abc
from abc import ABC, abstractmethod


class Command(ABC):
    @abstractmethod
    def _parse(self, command_input: str, **kwargs) -> list:
        pass

    @abstractmethod
    async def _execute(self, bot_brain, message, conversation, command_input, **kwargs):
        pass

    async def execute(self, bot_brain, message, conversation, command_input, **kwargs):
        inputs: list = self._parse(command_input, **kwargs)
        return await self._execute(bot_brain, message, conversation, inputs, **kwargs)

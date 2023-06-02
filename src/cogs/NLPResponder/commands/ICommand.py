import abc
from abc import ABC, abstractmethod


class ICommand(ABC):
    @abstractmethod
    def _parse(self, command_input: list, **kwargs) -> list:
        pass

    @abstractmethod
    async def _execute(self, bot_brain, message, conversation, command_inputs: list, **kwargs):
        pass

    async def execute(self, bot_brain, message, conversation, command_input, **kwargs):
        inputs: list = self._parse(command_input, **kwargs)
        return await self._execute(bot_brain, message, conversation, inputs, **kwargs)

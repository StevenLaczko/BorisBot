import discord

from src.cogs.NLPResponder.BotBrain import BotBrain
from src.cogs.NLPResponder.Command import Command
from src.cogs.NLPResponder.Context import Context
from src.cogs.NLPResponder.Conversation import Conversation


class RESPONDCommand(Command):
    def _parse(self, command_input: str, **kwargs) -> list:
        return [command_input]

    async def _execute(self, bot_brain, message, conversation, args, **kwargs):
        # returns the message sent
        message_str = args[0]
        msg = await conversation.channel.send(message_str)
        return msg


class REMEMBERCommand(Command):
    def _parse(self, command_input: str, **kwargs) -> list:
        return [command_input]

    async def _execute(self, bot_brain, message: discord.Message, conversation: Conversation, args, **kwargs):
        memory: str = args[0]
        do_emoji = True
        if do_emoji:
            await message.add_reaction('🤔')
        await bot_brain.save_memory(memory, conversation)


class MOODCommand(Command):
    def _parse(self, command_input: str, **kwargs) -> list:
        return [command_input]

    async def _execute(self, bot_brain: BotBrain, message, conversation: Conversation, args, **kwargs):
        conversation.mood = args[0]


commands = [RESPONDCommand(), REMEMBERCommand(), MOODCommand()]

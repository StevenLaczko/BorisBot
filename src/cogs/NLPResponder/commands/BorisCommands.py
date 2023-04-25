import discord

from src.cogs.NLPResponder.BotBrain import BotBrain
from src.cogs.NLPResponder.Command import Command
from src.cogs.NLPResponder.Context import Context
from src.cogs.NLPResponder.Conversation import Conversation


class RESPONDCommand(Command):
    def _parse(self, command_input: list, **kwargs) -> list:
        return command_input

    async def _execute(self, bot_brain, message, conversation, args, **kwargs):
        message_str = args[0]
        full_bot_response = kwargs["full_response"] if "full_response" in kwargs else None
        response_embed = kwargs["response_embed"] if "response_embed" in kwargs else None
        msg = await conversation.channel.send(message_str)
        if response_embed:
            conversation.update_memory_scores_from_embed(response_embed)
        else:
            conversation.update_memory_scores_from_str(msg.clean_content)
        conversation.replace_conversation_msg_by_id(msg.id, full_bot_response)


class REMEMBERCommand(Command):
    def _parse(self, command_input: list, **kwargs) -> list:
        return command_input

    async def _execute(self, bot_brain, message: discord.Message, conversation: Conversation, args, **kwargs):
        memory_str: str = args[0]
        bot_response_msg: str = kwargs["response_str"] if "response_str" in kwargs else None
        do_emoji = True
        if do_emoji:
            await message.add_reaction('🤔')
        await bot_brain.memory_manager.save_memory(memory_str, conversation, response_str=bot_response_msg)


class MOODCommand(Command):
    def _parse(self, command_input: list, **kwargs) -> list:
        return command_input

    async def _execute(self, bot_brain: BotBrain, message, conversation: Conversation, args, **kwargs):
        bot_brain.mood = args[0]
        return args[0]


class NEW_GOALCommand(Command):
    def _parse(self, command_input: list, **kwargs) -> list:
        return command_input

    async def _execute(self, bot_brain: BotBrain, message, conversation: Conversation, args, **kwargs):
        conversation.goal = args[0]
        await message.add_reaction('🫵')



commands = [RESPONDCommand(), REMEMBERCommand(), MOODCommand(), NEW_GOALCommand()]

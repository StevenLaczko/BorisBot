import json
from datetime import datetime
from typing import Union

import discord

from src.Boris import Boris
from src.cogs.NLPResponder import Prompts, GPTAPI, DiscordHelper
from src.cogs.NLPResponder.BotResponse import BotResponse
from src.cogs.NLPResponder.Context import Context
from src.cogs.NLPResponder.Memory import Memory
from src.helpers import StringMatchHelp
import logging

from MemoryPool import MemoryPool
from src.cogs.NLPResponder.Conversation import Conversation
from src.helpers.DiscordBot import DiscordBot
from src.helpers.logging_config import logger


class BotBrain:
    def __init__(self, bot,
                 memory_match_prob=0.8,
                 contexts_file_path="data/contexts.json",
                 memory_file_path="data/memories_dict.json",
                 hnsw_file_path="data/hnsw.pkl"):
        self.bot: DiscordBot = bot
        self.memory_match_prob = memory_match_prob
        self.memory_file_path = memory_file_path
        self.contexts_file_path = contexts_file_path
        self.hnsw_file_path = hnsw_file_path
        self.currentConversations: dict[int, Union[Conversation, None]] = {}
        self._memory_pool: MemoryPool = MemoryPool(
            memory_file_path=self.memory_file_path,
            hnsw_file_path=self.hnsw_file_path
        )
        self._contexts: dict = self.load_contexts()
        with open(self.contexts_file_path, 'r') as f:
            self._contexts: dict = self.create_contexts_from_json(json.load(f))

    def reply(self,
              message: discord.Message,
              conversation: Conversation,
              max_context_words=None,
              _memory=None,
              _mood=None):

        if not max_context_words:
            max_context_words = self.bot.settings["max_context_words"]
        if not _memory:
            _memory = self.get_memories_string(conversation)
        if not _mood:
            _mood = conversation.mood

        chatlog_context = await DiscordHelper.getContext(message.channel,
                                                         message,
                                                         bot=self.bot,
                                                         max_context_words=max_context_words)
        async with message.channel.typing():
            prompt = conversation.get_prompt(message, conversation)
            bot_response: BotResponse \
                = await GPTAPI.getGPTResponse(self.bot,
                                              message,
                                              chatlog_context,
                                              self.bot_brain.currentConversations[message.channel.id],
                                              self.bot.settings["id_name_dict"],
                                              memory=_memory,
                                              mood=_mood)
        if bot_response.response_str:
            logger.info(f"Response: {bot_response.response_str}")
            msg = await message.channel.send(bot_response.response_str)
            self.bot_brain.currentConversations[message.channel.id].bot_messageid_response[
                msg.id] = bot_response.full_response
        if bot_response.new_memory:
            if ADD_COMMAND_REACTIONS:
                await message.add_reaction('🤔')
            await self.bot_brain.save_memory(cstack, bot_response.new_memory)
        if bot_response.new_mood:
            if ADD_COMMAND_REACTIONS:
                await message.add_reaction('☝')
            self.bot_brain.set_mood(bot_response.new_mood)

    def start_conversation(self, channel: Union[discord.DMChannel, discord.TextChannel],
                           message_list: list[discord.Message], user_ids=None):
        self.currentConversations[channel.id] = Conversation(channel, timestamp=datetime.now())

    def isMessageInConversation(self, message: discord.Message):
        if message.channel.id in self.currentConversations and self.currentConversations[message.channel.id]:
            return self.currentConversations[message.channel.id]
        return None

    def get_memories_string(self, conversation: Conversation):
        memory_ids = conversation.context_stack.get_memory_ids()
        memory_strings = self._memory_pool.get_strings(memory_ids)
        # return f"```memories\n{newline_memories}\n```"
        if len(memory_strings) == 0:
            return ""
        else:
            newline_memories = '\n'.join(memory_strings)
            return f"```memories\n{newline_memories}\n```"

    def get_memories_related(self, memory: Memory):
        self._memory_pool.get_similar(memory)

    def get_memory_list(self):
        pass

    def save_memory(self, mem_str: str, conversation, memory_match_prob: float = None, shrink=True, explain=True):
        if not memory_match_prob:
            memory_match_prob = self.memory_match_prob
        for m in self.get_memory_list():
            isMatch, probability = await StringMatchHelp.fuzzyMatchString(mem_str, m, probMin=memory_match_prob)
            if isMatch:
                close = m
                logger.info(f"Not saving memory. Too close to {close}, probability {probability}")
                return
        id = self._memory_pool.add(mem_str)
        conversation.context_stack.save_memory(id)

    def make_convo_memory(self, conversation, conversation_log):
        _memory = GPTAPI.rememberGPT(self.bot, conversation_log, self.bot.settings["id_name_dict"])
        if _memory != "" and _memory is not None:
            logging.info(f"Storing memory: '{_memory}'")
            self.save_memory(_memory, conversation)
        else:
            logging.info(f"Storing no memories from conversation of length {len(conversation_log)}")

    def getMemories(self, pool: str) -> list[str]:
        context = self.getMemoryPool(pool)
        if context:
            return context.memories

    def getMemoryPool(self, pool: str) -> Union[Context, None]:
        if pool not in self.contexts:
            logging.error(f"Pool {pool} does not exist in bot memory.")
            return None
        return self.contexts[pool]

    def getMemoryPools(self, pools: list[str]) -> list[Context]:
        result = []
        for p in pools:
            if p not in self.contexts:
                logging.error(f"Pool {p} does not exist in bot memory.")
            else:
                result.append(self.contexts[p])
        return result

    def setMoodFromConvo(self, pool, conversation_log):
        self.mood = GPTAPI.getMood(self, conversation_log, self.contexts[pool].memories)
        logging.info(f"Setting mood from convo in context {pool} to {self.mood}")

    def setMood(self, context: Context, mood: str):
        context.mood = mood

import json
from datetime import datetime
from typing import Union

import discord

from src.Boris import Boris
from src.cogs.NLPResponder import Prompts, GPTAPI
from src.cogs.NLPResponder.Context import Context
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
                 memory_file_path="data/memories.json"):
        self.bot: DiscordBot = bot
        self.memory_match_prob = memory_match_prob
        self.memory_file_path = memory_file_path
        self.contexts_file_path = contexts_file_path
        self.currentConversations: dict[int, Union[Conversation, None]] = {}
        self._memory_pool: MemoryPool = MemoryPool(self.memory_file_path)
        self._contexts: dict = self.load_contexts()
        with open(self.contexts_file_path, 'r') as f:
            self._contexts: dict = self.create_contexts_from_json(json.load(f))


    def start_conversation(self, channel: Union[discord.DMChannel, discord.TextChannel], message_list: list[discord.Message], user_ids=None):
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

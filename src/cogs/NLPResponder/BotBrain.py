import json
from typing import Union

import discord

from src.cogs.NLPResponder import Prompts, GPTAPI
from src.cogs.NLPResponder.Context import Context
from src.helpers import StringMatchHelp
import logging

from src.cogs.NLPResponder.Conversation import Conversation


class BotBrain:
    def __init__(self,
                 memory_match_prob=0.8,
                 contexts_file_path="data/contexts.json",
                 memory_file_path="data/memories.json",
                 conversations=None):
        self.memory_match_prob = memory_match_prob
        self.memory_file_path = memory_file_path
        self.contexts_file_path = contexts_file_path
        self.currentConversations: dict[int, Union[Conversation, None]] = conversations if conversations else {}

    def isMessageInConversation(self, message: discord.Message):
        if message.channel.id in self.currentConversations and self.currentConversations[message.channel.id]:
            return self.currentConversations[message.channel.id]
        return None

    def getMemoriesString(self, conversation: Conversation):
        memory_str = "```Memories\n"
        if len(conversation.get_memory_str()) != 0:
            for m in self.contexts[pool].memories:
                memory_str += m + '\n'
        else:
            memory_str += "No memories.\n"
        memory_str += '```'

        return memory_str

    def saveMemory(self, mem_str: str, memoryMatchProb: float, shrink, explain):
        for m in self.memories:
            isMatch, probability = await StringMatchHelp.fuzzyMatchString(mem_str, m, probMin=memoryMatchProb)
            if isMatch:
                close = m
                logging.info(f"Not saving memory. Too close to {close}, probability {probability}")
                return

    def storeMemory(self, pool: str, bot, conversation_log):
        _memory = GPTAPI.rememberGPT(bot, conversation_log, self.contexts[pool].memories)
        if _memory != "" and _memory is not None:
            logging.info(f"Storing memory `{_memory} in pool {pool}")
            self.saveMemory(pool, _memory)
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

    def setMood(self, mood):
        self.mood = mood

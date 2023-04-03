import json
from typing import Union

from src.cogs.Respondtron import StringMatchHelp, GPTAPI, Prompts
import logging

from src.cogs.Respondtron.Conversation import Conversation


class Context:
    def __init__(self, name: str, memories: list[str] = None, mood: str = None, prompt_gpt_messages: list = None):
        self.name = name
        self.memories = memories if memories else []
        self.mood: str = mood
        self.currentConversations = []
        self.promptGPTMessages: Union[list, None] = prompt_gpt_messages if prompt_gpt_messages else self.getPrompt()

    def getPrompt(self):
        self.promptGPTMessages = Prompts.premade[self.name] if self.name in Prompts.premade else None

    def saveMemory(self, mem_str: str, memoryMatchProb: float, shrink, explain):
        for m in self.memories:
            isMatch, probability = await StringMatchHelp.fuzzyMatchString(mem_str, m, probMin=memoryMatchProb)
            if isMatch:
                close = m
                logging.info(f"Not saving memory. Too close to {close}, probability {probability}")
                return

        self.memories.append(mem_str.lower())
        if shrink:
            self.memories = GPTAPI.shrinkMemoriesGPT(self.memories, explain=explain)


class BotBrain:
    def __init__(self,
                 contexts: dict[str, Context] = None,
                 memory_match_prob=0.8,
                 contexts_file_path="data/contexts.json",
                 conversations=None):
        self.contexts: dict[str, Context] = contexts if contexts else {}
        if "main" not in self.contexts:
            self.contexts["main"] = Context("main")
        self.memoryMatchProb = memory_match_prob
        self.contextsFilePath = contexts_file_path
        self.currentConversations: dict[int, Conversation] = conversations if conversations else {}

    def getMemoriesString(self, pool):
        memory_str = "```Memories\n"
        if len(self.contexts[pool].memories) != 0:
            for m in self.contexts[pool].memories:
                memory_str += m + '\n'
        else:
            memory_str += "No memories.\n"
        memory_str += '```'

        return memory_str

    def setMood(self, context: str, mood: str):
        self.contexts[context].mood = mood

    def saveMemory(self, pool: str, mem_str: str, shrink=True, explain=True):
        if pool not in self.contexts:
            self.contexts[pool] = Context(pool)
        self.contexts[pool].saveMemory(mem_str, self.memoryMatchProb, shrink=shrink, explain=True)
        with open(self.contextsFilePath, 'w+') as contextsFile:
            contextsFile.write(json.dumps(self.contexts))

    def storeMemory(self, pool: str, bot, conversation_log):
        _memory = GPTAPI.rememberGPT(bot, conversation_log, self.contexts[pool].memories)
        if _memory != "" and _memory is not None:
            logging.info(f"Storing memory `{_memory} in pool {pool}")
            self.saveMemory(pool, _memory)
        else:
            logging.info(f"Storing no memories from conversation of length {len(conversation_log)}")

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

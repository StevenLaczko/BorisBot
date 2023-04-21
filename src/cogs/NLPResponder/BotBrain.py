import asyncio
import io
import json
import os
from datetime import datetime
from typing import Union

import discord

from src.cogs.NLPResponder import GPTHelper, DiscordHelper, GPTHelper
from src.cogs.NLPResponder.BotResponse import BotResponse
from src.cogs.NLPResponder.Context import Context
from src.cogs.NLPResponder.ContextStack import ContextStack
from src.cogs.NLPResponder.Memory import Memory
from src.cogs.NLPResponder.Prompt import Prompt
from src.helpers import StringMatchHelp
from src.helpers.Settings import settings
import logging

from src.cogs.NLPResponder.MemoryPool import MemoryPool
from src.cogs.NLPResponder.Conversation import Conversation
from src.helpers.DiscordBot import DiscordBot
from src.helpers.logging_config import logger


class BotBrain:
    def __init__(self, bot,
                 memory_match_prob=0.8,
                 context_dir="data/contexts/",
                 context_files=None,
                 commands=None,
                 memory_file_path="data/memories_dict.json",
                 memory_list_init=None,
                 hnsw_file_path="data/hnsw.pkl"):
        self.bot: DiscordBot = bot
        self.memory_file_path = memory_file_path
        self.contexts_dir = context_dir
        self.context_files = context_files
        self.commands = commands
        self.hnsw_file_path = hnsw_file_path
        self.currentConversations: dict[int, Union[Conversation, None]] = {}
        self._memory_pool: MemoryPool = MemoryPool(
            memory_file_path=self.memory_file_path,
            memory_list_init_path=memory_list_init,
            hnsw_file_path=self.hnsw_file_path
        )
        self.contexts: dict[str, Context] = self.load_contexts()
        self.vc_task: Union[asyncio.Task, None] = None

    def load_contexts(self) -> dict[str, Context]:
        contexts = {}
        for path in self.context_files:
            c_path = os.path.join(self.contexts_dir, path)
            new_context = self.create_context_from_json(c_path, self.commands)
            contexts[new_context.name] = new_context
        return contexts

    def create_context_from_json(self, filepath, command_funcs):
        with open(filepath, 'r') as f:
            context_dict = json.load(f)
        return Context(self._memory_pool, json_filepath=filepath, context_dict=context_dict, command_funcs=command_funcs)

    def create_conversation(self, channel):
        new_conversation = Conversation(channel, self._memory_pool, context_dict=self.contexts)
        self.currentConversations[channel.id] = new_conversation
        return new_conversation

    async def reply(self,
                    message: discord.Message,
                    conversation: Conversation,
                    max_context_words=None,
                    _memory=None,
                    _mood=None):

        if not _mood:
            _mood = conversation.mood
        if not max_context_words:
            max_context_words = settings.max_context_words

        chatlog_context = await DiscordHelper.getContext(message.channel,
                                                         message,
                                                         bot=self.bot,
                                                         max_context_words=max_context_words)
        chatlog_context.append(message)
        if not _memory:
            _memory = self.get_memories_string(conversation,
                                               context_string=GPTHelper.getContextGPTPlainMessages(self.bot,
                                                                                                   chatlog_context,
                                                                                                   settings.id_name_dict))
        gpt_chatlog: list = GPTHelper.getContextGPTMix(self.bot, chatlog_context, conversation, settings.id_name_dict)
        #dynamic_prompt = ##### TODO
        prompt: Prompt = conversation.get_prompt(message, conversation)
        async with message.channel.typing():
            bot_response: BotResponse = self.getBotResponse(prompt.get_prompt(), gpt_chatlog)
        returns = await conversation.context_stack.execute_commands(self, message, conversation, bot_response.commands)
        for r in returns:
            if r[0] == "RESPOND":
                conversation.bot_messageid_response[r[1].id] = bot_response.full_response

    def getBotResponse(self, prompt: str, gpt_chatlog: list, temperature=None, freq_pen=None, model=None):
        gpt_input = GPTHelper.buildGPTMessageLog(prompt, *gpt_chatlog)
        response_str = GPTHelper.promptGPT(gpt_input, temperature, freq_pen, model)["string"]
        return BotResponse(response_str)

    def startConversation(self, channel: Union[discord.DMChannel, discord.TextChannel],
                          message_list: list[discord.Message], user_ids=None):
        self.currentConversations[channel.id] = Conversation(channel, timestamp=datetime.now())

    def isMessageInConversation(self, message: discord.Message):
        if message.channel.id in self.currentConversations and self.currentConversations[message.channel.id]:
            return self.currentConversations[message.channel.id]
        return None

    def get_memories_string(self, conversation: Conversation, context_string: str = None):
        memory_ids = conversation.context_stack.get_memory_ids()
        context_memories = None
        if context_string:
            candidate_context_memories_ids = self._memory_pool.get_similar_mem_ids(GPTHelper.getEmbedding(context_string), k=3)
            context_memory_ids = []
            memory_id_dict = {x: 0 for x in memory_ids}
            for x in candidate_context_memories_ids:
                if x not in memory_id_dict:
                    context_memory_ids.append(x)
            context_memories = self._memory_pool.get_strings(context_memory_ids)
            logger.info(f"Contextual memories:\n{context_memories}")
        memory_strings = self._memory_pool.get_strings(memory_ids)
        if context_memories:
            memory_strings.extend(context_memories)
        newline_memories = '\n'.join(memory_strings)
        return f"```memories\n{newline_memories}\n```" if len(memory_strings) > 0 else ""

    def get_memories_related(self, memory: Memory):
        self._memory_pool.get_similar(memory.embedding)

    def get_memory_list(self):
        pass

    async def save_memory(self, mem_str: str, conversation: Conversation, memory_match_prob: float = None, shrink=True, explain=True):
        m = Memory(mem_str)
        if not memory_match_prob:
            memory_match_prob = settings.memory_match_prob
        m_id_dist_list = self._memory_pool.get_similar(m.embedding, 1)
        m_id = None
        similarity = None
        if len(m_id_dist_list) > 0:
            m_id = m_id_dist_list[0][0]
            similarity = m_id_dist_list[0][1]
            similar_mem: Memory = self._memory_pool.memories[m_id]
            if similarity > memory_match_prob:
                logger.info(f"Not saving memory. Too close to {similar_mem.string}, similarity {similarity}")
                return
        self._memory_pool.add(m)
        conversation.context_stack.add_memory(m.id)

    def getMemories(self) -> list[str]:
        return [m.string for m in self._memory_pool.memories.values()]

    def getMemoriesFromStack(self, stack: ContextStack) -> list[Memory]:
        return [self._memory_pool.memories[x] for x in stack.get_memory_ids()]

    def getMemoryPools(self, pools: list[str]) -> list[Context]:
        result = []
        for p in pools:
            if p not in self.contexts:
                logging.error(f"Pool {p} does not exist in bot memory.")
            else:
                result.append(self.contexts[p])
        return result

    def setMoodFromConvo(self, pool, conversation_log):
        self.mood = GPTHelper.getMood(self, conversation_log, self.contexts[pool].memories)
        logging.info(f"Setting mood from convo in context {pool} to {self.mood}")

    def setMood(self, context: Context, mood: str):
        context.mood = mood

    def vc_disconnect(self):
        self.vc_task.cancel()

    def vc_callback(self, data):
        self.audio_retrieve_start = datetime.now()
        # Decode the Opus data to PCM
        pcm_data, _ = discord.opus.decode(data, 3840)

        # Process the PCM data as needed
        # For example, write it to a file using soundfile
        f = io.BytesIO(pcm_data)
        from pydub import AudioSegment
        AudioSegment.from_file(f, format='WAV')

        # Do something with the WAV data, such as sending it to a speech-to-text API
        text = GPTHelper.speech_to_text(wav_bytes)

    async def connect_to_vc(self, vc: discord.VoiceChannel):
        discord.opus.load_opus(settings.opus)
        vc_con = await vc.connect()
        loop = asyncio.get_event_loop()
        self.vc_task = loop.create_task(vc_con.listen(self.vc_callback))


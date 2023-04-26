import asyncio
import io
import json
import os
from datetime import datetime
from typing import Union

import discord

from src.cogs.NLPResponder import GPTHelper, DiscordHelper, GPTHelper
from src.cogs.NLPResponder.MemoryManager import MemoryManager
from src.cogs.NLPResponder.BotCommands import BotCommands
from src.cogs.NLPResponder.Context import Context
from src.cogs.NLPResponder.ContextStack import ContextStack
from src.cogs.NLPResponder.Memory import Memory, cosine_similarity
from src.cogs.NLPResponder.Prompt import Prompt
from src.cogs.NLPResponder.VCHandler import VCHandler
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
        self.contexts_dir = context_dir
        self.context_files = context_files
        self.commands = commands
        self.hnsw_file_path = hnsw_file_path
        self.currentConversations: dict[int, Union[Conversation, None]] = {}
        self.memory_manager: MemoryManager = MemoryManager(memory_file_path, hnsw_file_path,
                                                           memory_list_init=memory_list_init,
                                                           context_files=context_files)
        self.contexts: dict[str, Context] = self.load_contexts()
        self.mood: str = ""
        self.vc_handler = VCHandler()

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
        return Context(self.memory_manager, json_filepath=filepath, context_dict=context_dict,
                       command_funcs=command_funcs)

    def create_conversation(self, channel):
        new_conversation = Conversation(channel, self.memory_manager, context_dict=self.contexts)
        self.currentConversations[channel.id] = new_conversation
        return new_conversation

    async def reply(self,
                    message: discord.Message,
                    conversation: Conversation,
                    max_context_words=None,
                    convo_memories=None,
                    _mood=None):
        if not _mood:
            _mood = self.mood
        if not max_context_words:
            max_context_words = settings.max_context_words

        conversation.users[message.author.id] = True
        conversation.num_msg_since_response = 0

        # get chatlog
        chatlog_context = await DiscordHelper.getContext(message.channel,
                                                         message,
                                                         bot=self.bot,
                                                         max_context_words=max_context_words)
        chatlog_context.append(message)
        gpt_chatlog: list = GPTHelper.getContextGPTMix(self.bot,
                                                       chatlog_context,
                                                       conversation,
                                                       settings.id_name_dict,
                                                       write_timestamp_for_bot=False,
                                                       bot_name="Response")
        #gpt_chatlog = GPTHelper.getContextGPTPlainMessages(self.bot, chatlog_context, settings.id_name_dict, markdown=False)
        #gpt_chatlog = "\n\nConversation:\n" + gpt_chatlog

        # get memories
        context_memories = self.memory_manager.get_context_memories(
            GPTHelper.getContextGPTPlainMessages(self.bot, chatlog_context, settings.id_name_dict),
            conversation=conversation)
        if not convo_memories:
            convo_memories = self.memory_manager.get_memories_from_ids(conversation.get_memory_ids())
        convo_memories.extend(context_memories)
        memory_str = self.memory_manager.get_memories_string(convo_memories)


        # get prompt, build llm inputs
        prompt: Prompt = conversation.get_prompt(message, conversation)
        dynamic_prompts = {
            "CONVERSATION_INFO": GPTHelper.getMessageableString(conversation.channel, settings.id_name_dict),
            "TIME_INFO": GPTHelper.getCurrentTimeString(),
            "MEMORY": memory_str,
            "GOAL_INFO": f"Current goal: {conversation.goal}" if conversation.goal else "Current goal: None"
        }
        bot_inputs = [prompt.get_prompt(dynamic_prompts)]
        bot_inputs.extend(gpt_chatlog)

        bot_commands: BotCommands = self.getBotCommands(bot_inputs)
        logger.debug(f"Full response:\n{bot_commands.full_response}")

        response_str = bot_commands.commands["RESPOND"][0] if "RESPOND" in bot_commands.commands else None
        response_embed = GPTHelper.getEmbedding(response_str) if response_str else None
        await self.execute_bot_commands(message, conversation, bot_commands,
                                        response_str=response_str,
                                        response_embed=response_embed,
                                        full_response=bot_commands.full_response)

        self.add_contextual_memory_if_best(convo_memories, context_memories, response_embed, conversation, bot_commands)
        if self.vc_handler.is_connected() and message.channel == self.vc_handler.vc_text_channel:
            self.vc_handler.respond(response_str)

    def add_contextual_memory_if_best(self, convo_memories, context_memories, response_embed, conversation, bot_commands):
        if "RESPOND" not in bot_commands.commands or not response_embed:
            return

        best_memory = None
        best_score = 0
        for m in convo_memories:
            sim = cosine_similarity(response_embed, m.embedding)
            if sim > best_score:
                best_memory = m
                best_score = sim
            # auto fix memories not already scored
            self.verify_and_fix_memory(m, response_embed, conversation)

        if best_memory in context_memories:
            conversation.context_stack.add_memory_to_contexts(best_memory)
            logger.info(
                f"This context memory was relevant enough to be added to short-term memory:\n{str(best_memory)}")

    def verify_and_fix_memory(self, m: Memory, response_embed: list, conversation: Conversation):
        mem_changed = False
        before = m.string
        m.string = m.string.strip(' \n')
        if before != m.string:
            mem_changed = True
        if m.score == 0:
            self.memory_manager.update_mem_score_from_response_embed(response_embed, m)
            mem_changed = True
        if mem_changed:
            self.memory_manager.save_memories_to_json()

    async def execute_bot_commands(self, message, conversation, bot_commands, **kwargs):
        # TODO this kwarg stuff is gross, fix. maybe have commands take kwargs.
        response_embed_key = "response_embed"
        response_embed = None
        if response_embed_key in kwargs:
            response_embed = kwargs[response_embed_key]

        for c_name in bot_commands.commands:
            bot_commands.commands[c_name].append(kwargs)

        returns: dict = await conversation.execute_commands(self, message, bot_commands.commands)
        for command_name in returns.keys():
            if command_name == "RESPOND":
                bot_msg_id = returns[command_name].id
                conversation.replace_conversation_msg_by_id(bot_msg_id, bot_commands.full_response)
            if command_name == "MOOD":
                pass
                # await self.bot.change_presence(status=returns[c_name])
                # TODO discord.ActivityType.listening

    def get_message_conversation(self, message: discord.Message):
        if message.channel.id in self.currentConversations:
            return self.currentConversations[message.channel.id]
        return None

    def getBotCommands(self, inputs: list, temperature=None, freq_pen=None, model=None):
        # gpt_chatlog is a list of
        #   dict openai json messages,
        #   strings (which will be user messages),
        #   or another list of one of the above
        gpt_input = GPTHelper.buildGPTMessageLog(*inputs)
        logger.debug(f"{inputs}")
        response_str = GPTHelper.promptGPT(gpt_input, temperature, freq_pen, model)["string"]
        return BotCommands(response_str)

    def startConversation(self, channel: Union[discord.DMChannel, discord.TextChannel],
                          message_list: list[discord.Message], user_ids=None):
        self.currentConversations[channel.id] = Conversation(channel, timestamp=datetime.now())

    async def connect_to_vc(self, vc, text_channel):
        await self.vc_handler.connect_to_vc(vc, text_channel)
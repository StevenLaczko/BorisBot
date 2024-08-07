import asyncio
import json
import os
from datetime import datetime, timedelta
from typing import Union
import discord
import requests

from src import GPTExceptions
from src.helpers import GPTHelper, DiscordHelper
from src.cogs.NLPResponder.Memory.MemoryManager import MemoryManager
from src.cogs.NLPResponder.commands.BotCommands import BotCommands
from src.cogs.NLPResponder.Context import Context
from src.cogs.NLPResponder.Memory.Memory import Memory, cosine_similarity
from src.cogs.NLPResponder.Prompt import Prompt
from src.cogs.NLPResponder.VCHandler import VCHandler
from src.helpers.Settings import settings

from src.cogs.NLPResponder.Conversation import Conversation
from src.helpers.DiscordBot import DiscordBot
from src.helpers.logging_config import logger

import sys
sys.path.insert(0, './discord.py')


class BotBrain:
    """
    A BotBrain object is the core of a chatbot.
    It holds onto memory information, commands, current conversations, contexts, etc.
    """
    def __init__(self, bot,
                 context_dir="data/contexts/",
                 context_files=None,
                 commands=None,
                 memory_file_path="data/memories_dict.json",
                 memory_list_init=None,
                 hnsw_file_path="data/hnsw.pkl"):
        """

        :param bot: The discord "bot" object belonging to the chatbot.
        :param context_dir: The directory where context json files are stored.
        :param context_files:
        :param commands:
        :param memory_file_path:
        :param memory_list_init: a newline separated list of strings to initialize the bot's memory with
        :param hnsw_file_path:
        """
        self.bot: DiscordBot = bot
        self.contexts_dir = context_dir
        self.context_files = context_files
        self.commands = commands
        self.hnsw_file_path = hnsw_file_path
        self.currentConversations: dict[int, Union[Conversation, None]] = {}
        self.memory_manager: MemoryManager = MemoryManager(memory_file_path, hnsw_file_path,
                                                           memory_list_init=memory_list_init)
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

    def delete_memory(self, mem_id):
        #TODO implement those two funcs
        for c in self.contexts.values():
            if mem_id in c.get_memory_ids():
                c.remove_memory_with_id(mem_id)
        for convo in self.currentConversations.values():
            if mem_id in convo.get_memory_ids():
                convo.remove_memory_with_id(mem_id)
        self.memory_manager.delete_memory(mem_id)

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

        if asyncio.current_task().cancelled():
            logger.info("Cancelled reply successfully.")
            return

        conversation.user_num_messages_since_last_msg[message.author.id] = 0
        for user, num_msgs_since_last_sent_msg in conversation.user_num_messages_since_last_msg.items():
            if num_msgs_since_last_sent_msg > 10:
                del conversation.user_num_messages_since_last_msg[user]

        # get chatlog
        chatlog_context = await DiscordHelper.getContext(message.channel,
                                                         message,
                                                         time_cutoff=timedelta(hours=1),
                                                         bot=self.bot,
                                                         max_context_words=max_context_words)
        chatlog_context.append(message)
        gpt_chatlog: list = GPTHelper.getContextGPTMix(self.bot,
                                                       chatlog_context,
                                                       conversation,
                                                       settings.id_name_dict,
                                                       write_timestamp_for_bot=False,
                                                       bot_prepend_str="!RESPOND ")
        #gpt_chatlog = GPTHelper.getContextGPTPlainMessages(self.bot, chatlog_context, settings.id_name_dict, markdown=False)
        #gpt_chatlog = "\n\nConversation:\n" + gpt_chatlog
        chatlog_plaintext = GPTHelper.getContextGPTPlainMessages(self.bot,
                                                                 chatlog_context,
                                                                 settings.id_name_dict,
                                                                 markdown=False,
                                                                 write_bot_name=False,
                                                                 write_user_name=False)
        chatlog_embed = GPTHelper.getEmbedding(chatlog_plaintext)

        if asyncio.current_task().cancelled():
            logger.info("Cancelled reply successfully.")
            return

        # get memories
        context_memories = self.memory_manager.get_context_memories(chatlog_embed, conversation=conversation, n=3)
        if not convo_memories:
            convo_memories = self.memory_manager.get_memories_from_ids(conversation.get_memory_ids())
        convo_memories.extend(context_memories)
        self.memory_manager.update_memories_score_from_memory_list(chatlog_embed, convo_memories)
        memory_str = self.memory_manager.get_memories_string(convo_memories)

        if asyncio.current_task().cancelled():
            logger.info("Cancelled reply successfully.")
            return

        # get prompt, build llm inputs
        prompt: Prompt = conversation.get_prompt(message, conversation)
        dynamic_prompts = {
            "CONVERSATION_INFO": GPTHelper.getMessageableString(conversation.channel, settings.id_name_dict),
            "TIME_INFO": GPTHelper.getCurrentTimeString(),
            "MEMORY": memory_str,
            "GOAL_INFO": f"Current goal: {conversation.goal}" if conversation.goal else "Current goal: Chat"
        }
        sys_prompt, user_prompt = prompt.get_prompt(dynamic_prompts)
        llm_sys_input = [sys_prompt]
        llm_user_input = [user_prompt]
        llm_user_input.extend(gpt_chatlog)
        assistant_response_respond_prepend = ""
        if len(assistant_response_respond_prepend) > 0:
            llm_user_input.extend(
                GPTHelper.createGPTMessage(assistant_response_respond_prepend, GPTHelper.Role.ASSISTANT))

        prompt_str = llm_user_input[0] + '\n' + llm_sys_input[0] + '\n'.join([str(x) for x in gpt_chatlog])
        logger.debug("PROMPT START")
        logger.debug(prompt_str)
        logger.debug("PROMPT END")
        try:
            async with message.channel.typing():
                response_str = await self.prompt_bot(llm_user_input, system_inputs=llm_sys_input)
        except (GPTExceptions.ContextLimitException, asyncio.TimeoutError, requests.RequestException) as e:
            # Log the exception details
            logger.error(f"Exception of type {type(e).__name__} occurred: {str(e)}")
            await message.add_reaction('❌')
            return

        response_str = assistant_response_respond_prepend + response_str
        bot_commands: BotCommands = self.getBotCommands(response_str)

        if asyncio.current_task().cancelled():
            logger.info("Cancelled reply successfully.")
            return

        logger.debug(f"Full response:\n{bot_commands.full_response}")

        # response_embed = GPTHelper.getEmbedding(response_str) if response_str else None
        await self.execute_bot_commands(message, conversation, bot_commands,
                                        compare_embed=chatlog_embed,
                                        full_response=bot_commands.full_response)

        self.add_contextual_memory_if_best(convo_memories, context_memories, chatlog_embed, conversation, bot_commands)

        if self.vc_handler.is_connected() and message.channel == self.vc_handler.vc_text_channel:
            response_str = bot_commands.commands["RESPOND"][0] if "RESPOND" in bot_commands.commands else None
            self.vc_handler.respond(response_str)

    def add_contextual_memory_if_best(self, convo_memories, context_memories, compare_embed, conversation, bot_commands):
        if "RESPOND" not in bot_commands.commands or not compare_embed:
            return

        best_memory = None
        best_score = 0
        for m in convo_memories:
            sim = cosine_similarity(compare_embed, m.embedding)
            if sim > best_score:
                best_memory = m
                best_score = sim
            # auto fix memories not already scored
            self.verify_and_fix_memory(m, compare_embed)

        if best_memory in context_memories:
            conversation.context_stack.add_memory_to_contexts(best_memory)
            logger.info(
                f"This context memory was relevant enough to be added to short-term memory:\n{str(best_memory)}")

    def verify_and_fix_memory(self, m: Memory, compare_embed: list):
        mem_changed = False
        before = m.string
        m.string = m.string.strip(' \n')
        if before != m.string:
            mem_changed = True
        if m.score == 0:
            self.memory_manager.update_memories_score_from_memory_list(compare_embed, [m])
            mem_changed = True
        if mem_changed:
            self.memory_manager.save_memories_to_json()

    async def execute_bot_commands(self, message, conversation, bot_commands, **kwargs):
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

    async def prompt_bot(self, inputs: list, system_inputs: list = None, temperature=None, freq_pen=None, model=None):
        # gpt_chatlog is a list of
        #   dict openai json messages,
        #   strings (which will be user messages),
        #   or another list of one of the above
        gpt_input = GPTHelper.buildGPTMessageLog(*inputs, system=system_inputs)
        logger.debug(f"{gpt_input}")
        response_str = (await GPTHelper.promptGPT(gpt_input, temperature, freq_pen, model))["string"]


        return response_str

    def getBotCommands(self, response_str: str):
        return BotCommands(response_str)

    def startConversation(self, channel: Union[discord.DMChannel, discord.TextChannel],
                          message_list: list[discord.Message], user_ids=None):
        self.currentConversations[channel.id] = Conversation(channel, timestamp=datetime.now())

    async def connect_to_vc(self, vc, text_channel):
        await self.vc_handler.connect_to_vc(vc, text_channel)

import datetime
import discord

from src.helpers import GPTHelper
from src.cogs.NLPResponder.Context import Context
from src.cogs.NLPResponder.ContextStack import ContextStack
from src.helpers.logging_config import logger

from src.cogs.NLPResponder.Memory.Memory import Memory
from src.cogs.NLPResponder.Memory.Memory import cosine_similarity


class Conversation:
    def __init__(self, channel, memory_manager, context_dict: dict[str, Context] = None, context_stack=None, timestamp=None, message_dict=None, mood=None):
        self.timestamp: datetime = timestamp if timestamp else datetime.datetime.now()
        self.bot_messageid_response: dict = message_dict if message_dict else {}
        self.channel = channel
        self.context_dict = context_dict
        self.memory_manager = memory_manager
        self.context_stack: ContextStack = context_stack if context_stack else self.init_context_stack()
        self.goal = ""
        self.num_msg_since_response = 0
        self.user_num_messages_since_last_msg = {}
        self.responding_task = None
        #I think I want to cancel his current response when he gets a new message instead. He'll make a lot more sense.
        #self.mutex = Lock() # use with mutex: for getting replying so he doesn't reply to a bunch of stuff in a row

    def init_context_stack(self):
        return ContextStack(self.context_dict, self.memory_manager)

    def get_memory_ids(self):
        return self.context_stack.get_memory_ids()

    def get_prompt(self, message, conversation):
        return self.context_stack.get_combined_prompt(message, conversation)

    def update_memory_scores_from_str(self, response_str: str):
        embed = GPTHelper.getEmbedding(response_str)
        self.memory_manager.update_memories_scores_from_ids(embed, self.context_stack.get_memory_ids())

    def update_memory_scores_from_embed(self, response_embed: list):
        self.memory_manager.update_memories_scores_from_ids(response_embed, self.context_stack.get_memory_ids())

    def should_reply_to_convo_message(self):
        logger.warning("Message received in convo channel")
        self.timestamp = datetime.datetime.now()
        if self.num_msg_since_response >= self.get_num_users():
            logger.info(f"msgs since response: {self.num_msg_since_response}\nnum users in convo: {self.get_num_users()}\nResponding.")
            return True
        return False

    def get_num_users(self):
        return len(self.user_num_messages_since_last_msg)

    def has_message(self, message: discord.Message):
        if message in self.channel:
            return True
        return False

    def replace_conversation_msg_by_id(self, msg_id: int, replacement_str: str):
        self.bot_messageid_response[msg_id] = replacement_str

    def add_memory(self, memory: Memory, compare_str: str = None, compare_embed: list = None):
        if memory.score == 0 and (compare_embed or compare_str):
            if compare_embed:
                memory.score = cosine_similarity(compare_embed, memory.embedding)
            else:
                memory.score = cosine_similarity(GPTHelper.getEmbedding(compare_str), memory.embedding)
        self.context_stack.add_memory_to_contexts(memory)

    def save_context_memories(self):
        self.context_stack.save_memories_to_contextfiles()

    async def execute_commands(self, bot_brain, message, commands: dict[str, list]):
        return await self.context_stack.execute_commands(bot_brain, message, self, commands)



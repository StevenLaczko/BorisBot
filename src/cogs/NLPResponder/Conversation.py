import datetime

from src.cogs.NLPResponder.Context import Context
from src.cogs.NLPResponder.ContextStack import ContextStack
from threading import Lock


class Conversation:
    def __init__(self, channel, memory_pool, context_dict: dict[str, Context] = None, context_stack=None, timestamp=None, message_dict=None, mood=None):
        self.timestamp: datetime = timestamp if timestamp else datetime.datetime.now()
        self.bot_messageid_response: dict = message_dict if message_dict else {}
        self.channel = channel
        self.context_dict = context_dict
        self.memory_pool = memory_pool
        self.mood: str = mood
        self.context_stack: ContextStack = context_stack if context_stack else self.init_context_stack()
        self.mutex = Lock() # use with mutex: for getting replying so he doesn't reply to a bunch of stuff in a row

    def init_context_stack(self):
        return ContextStack(self.context_dict, self.memory_pool)

    def get_memory_ids(self):
        return self.context_stack.get_memory_ids()

    def get_prompt(self, message, conversation):
        return self.context_stack.get_combined_prompt(message, conversation)



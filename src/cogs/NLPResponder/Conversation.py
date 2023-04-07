import datetime

from src.cogs.NLPResponder.Context import Context
from src.cogs.NLPResponder.ContextStack import ContextStack


class Conversation:
    def __init__(self, channel, message_list, context_dict: dict[str, Context], memory_pool, context=None, context_stack=None, timestamp=None, message_dict=None, mood=None):
        self.timestamp: datetime = timestamp if timestamp else datetime.datetime.now()
        self.bot_messageid_response: dict = message_dict if message_dict else {}
        self.channel = channel
        self.context_dict = context_dict
        self.memory_pool = memory_pool
        self.mood: str = mood
        self.context_stack: ContextStack = context_stack if context_stack else self.init_context_stack()

    def init_context_stack(self):
        cstack = []
        for c in self.context_dict.values():
            if c.is_triggered(self):
                cstack.append(c)

        return ContextStack(self.context_dict, self.memory_pool)

    def get_memory_ids(self):
        return self.context_stack.get_memory_ids()



import datetime
from src.cogs.NLPResponder.ContextStack import ContextStack


class Conversation:
    def __init__(self, channel, context=None, context_stack=None, timestamp=None, message_dict=None, mood=None):
        self.timestamp: datetime = timestamp if timestamp else datetime.datetime.now()
        self.bot_messageid_response: dict = message_dict if message_dict else {}
        self.channel = channel
        self.context_stack: ContextStack = context_stack if context_stack else ContextStack(context)
        self.mood: str = mood

    def get_memory_str(self):
        pass


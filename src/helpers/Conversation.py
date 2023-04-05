import datetime


class Conversation:
    def __init__(self, messageable, timestamp=None, message_dict=None):
        self.timestamp: datetime = timestamp if timestamp else datetime.datetime.now()
        self.bot_messageid_response: dict = message_dict if message_dict else {}
        self.channel = messageable

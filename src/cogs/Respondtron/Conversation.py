import datetime

import discord


class Conversation:
    def __init__(self, guild, brain_context: str, timestamp=None, message_dict=None):
        self.timestamp: datetime = timestamp if timestamp else datetime.datetime.now()
        self.bot_messageid_response: dict = message_dict if message_dict else {}
        self.guild: discord.Guild = guild
        self.context: str = brain_context




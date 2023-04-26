import datetime
import json
import os
import random
from typing import Union

import discord
import pytz
from discord.ext import commands

import src.cogs.NLPResponder.GPTHelper as GPTHelper
from src.cogs.NLPResponder.BotBrain import BotBrain
from src.cogs.NLPResponder.BotCommands import BotCommands
from src.cogs.NLPResponder.Context import Context
from src.cogs.NLPResponder.Conversation import Conversation
from src.cogs.NLPResponder.commands import BorisCommands
from src.helpers import DiscordBot
from src.helpers.logging_config import logger

ADMIN_ROLE_ID = 658116626712887316
CONTEXT_LEN_DEF = 5
MAX_CONTEXT_WORDS = 100
MAX_CONVO_WORDS = 200
MEMORY_CHANCE = 1
CONVO_END_DELAY = datetime.timedelta(minutes=10)
ADD_COMMAND_REACTIONS = True
MEMORY_FILEPATH = "data/memories_dict.json"

# TODO Add undo (at least to addResponse)
class NLPResponder(commands.Cog):
    def __init__(self, bot: DiscordBot.DiscordBot, prefix, memory_filepath=None, memory_list_init=None):
        self.bot = bot
        self.prefix: str = prefix
        self.memory_file_path = DiscordBot.getFilePath(memory_filepath)
        context_dir = "data/contexts/"
        c_files = ["main-context.json"]
        self.bot_brain = BotBrain(self.bot, context_dir=context_dir, context_files=c_files, commands=BorisCommands.commands, memory_file_path=memory_filepath, memory_list_init=memory_list_init)
        self.vc = None

        # load memories
        if os.path.isfile(self.memory_file_path):
            with open(self.memory_file_path, 'r') as memoryFile:
                self.memory: list[str] = json.loads(memoryFile.read())

    # EVENTS

    # on_message listens for incoming messages starting with an @(botname) and then responds to them
    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        current_convo = self.bot_brain.get_message_conversation(message)
        if current_convo:
            current_convo.num_msg_since_response += 1

        # consider conversations over after 3 minutes of boris not responding
        conversationsToStop = []
        now = datetime.datetime.now()
        for c in self.bot_brain.currentConversations:
            if not self.bot_brain.currentConversations[c]:
                continue
            dt = CONVO_END_DELAY
            if self.bot_brain.currentConversations[c].timestamp + dt < now:
                channel = self.bot_brain.currentConversations[c].channel
                if not channel:
                    logger.error(f"Conversation does not have channel attribute")
                else:
                    conversationsToStop.append(channel)

        if message.author.id == self.bot.user.id:
            return

        if message.clean_content.strip()[0] != self.prefix:
            await self.handle_response_situations(message, current_convo)

        for c in conversationsToStop:
            await self.stop_conversation(c)

    async def handle_response_situations(self, message, conversation):
        mention_ids = [m.id for m in message.mentions]
        if "boris stop" in message.clean_content.lower():
            await self.stop_conversation(message.channel)
        elif isinstance(message.channel, discord.DMChannel):
            logger.info("Received message in DM")
            await self.replyToMessage(message, conversation)
        elif self.bot.user.id in mention_ids:
            logger.warning(self.bot.user.name + " mention DETECTED")
            await self.replyToMessage(message, conversation)
        elif "boris" in message.clean_content.lower():
            logger.warning("I heard my name.")
            if conversation or 0.2 > random.random():
                await self.replyToMessage(message)
        elif conversation:
            logger.warning("Message received in convo channel")
            conversation.timestamp = datetime.datetime.now()
            if 0.3 > random.random() or conversation.num_msg_since_response >= conversation.get_num_users():
                await self.replyToMessage(message, conversation)
        # TODO 5% chance asks GPT if it's relevant to Boris or his memories
        elif 0.05 > random.random():
            await self.replyToMessage(message, conversation)

    # COMMANDS

    @commands.command(name="remember", help="Remember.")
    @commands.is_owner()
    async def remember(self, ctx):
        await self.storeMemory(
            await self.getConvoContext(ctx.channel, after=None, ignore_list=self.bot.settings["ignore_list"]))

    @commands.command(name="joinvc", help="Join a vc, give him an id")
    async def join_vc(self, ctx, vc_id):
        vc_id = int(vc_id)
        if vc_id is None:
            vc: discord.VoiceChannel = ctx.author.voice.channel
        else:
            vc = ctx.guild.get_channel(vc_id)
        await self.bot_brain.connect_to_vc(vc, ctx.channel)

    @commands.command(name="disconnect", help="Disconnect from vc")
    async def disconnect(self, ctx):
        if self.bot_brain.vc_handler.is_connected():
            self.bot_brain.vc_handler.vc_disconnect()
        else:
            await ctx.message.reply("I ain't connected to a vc!")

    # METHODS

    async def stop_conversation(self, channel):
        if channel.type is discord.ChannelType.private:
            logger.info(
                f"{CONVO_END_DELAY} passed. Ending convo in DM with {channel.recipient if channel.recipient else 'unknown user'}")
        else:
            logger.info(f"{CONVO_END_DELAY} passed. Ending convo in {channel.name}")
        self.bot_brain.currentConversations[channel.id] = None

    async def replyToMessage(self, message, conversation=None):
        logger.info("Responding")
        if not conversation:
            conversation = self.bot_brain.create_conversation(message.channel)
        async with message.channel.typing():
            await self.bot_brain.reply(message, conversation)

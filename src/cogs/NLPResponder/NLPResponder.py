import asyncio
import datetime
import json
import os
import random

import discord
from discord.ext import commands

from src.cogs.NLPResponder.BotBrain import BotBrain
from src import BorisCommands
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

        clean_content = message.clean_content.strip()
        if len(clean_content) > 0 and clean_content[0] != self.prefix:
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
            if conversation or 0.05 > random.random():
                await self.replyToMessage(message)
        elif conversation and conversation.should_reply_to_convo_message():
            if conversation.responding_task:
                logger.info("Message received, canceling and restarting response.")
                conversation.responding_task.cancel()
                conversation.responding_task = None
            await self.replyToMessage(message, conversation)
        # TODO 5% chance asks GPT if it's relevant to Boris or his memories
        elif 0.0005 > random.random():
            await self.replyToMessage(message, conversation)

    # COMMANDS

    # @commands.command(name="remember", help="Remember.")
    # @commands.is_owner()
    # async def remember(self, ctx):
    #     await self.bot_brain.

    @commands.is_owner()
    @commands.command(name="listmemories", help="listmemories <num memories, default 10> <newest, default/oldest>")
    async def list_memories(self, ctx, num_mems=10, order="newest"):
        if not isinstance(num_mems, int):
            await ctx.channel.send("The first argument needs to be an integer.")
            return
        if not (order == "newest" or order == "oldest"):
            await ctx.channel.send("The second argument needs to be either 'newest' or 'oldest'.")
            return
        sorted_mems = self.bot_brain.memory_manager.get_memory_list(num_mems, order == "newest")
        await ctx.channel.send('\n'.join([str(x) for x in sorted_mems]))

    @commands.is_owner()
    @commands.command(name="delmemory", help="delmemory <id>")
    async def del_memory(self, ctx, mem_id):
        mem_id = int(mem_id)
        try:
            self.bot_brain.delete_memory(mem_id)
        except KeyError:
            await ctx.channel.send("ID not found.")
            return
        await ctx.channel.send("Memory deleted.")

    @commands.command(name="joinvc", help="Join a vc. Be in the vc, or give an id, or a channel mention.")
    async def join_vc(self, ctx, x: str):
        try:
            vc_id = int(x)
        except Exception:
            vc_id = None
        if not x:
            vc: discord.VoiceChannel = ctx.author.voice.channel
        elif vc_id:
            vc = ctx.guild.get_channel(vc_id)
        else:
            vc: discord.VoiceChannel = ctx.message.channel_mentions[0]
        await self.bot_brain.connect_to_vc(vc, ctx.channel)

    @commands.command(name="disconnect", help="Disconnect from vc")
    async def disconnect(self, ctx):
        if self.bot_brain.vc_handler.is_connected():
            await self.bot_brain.vc_handler.vc_disconnect()
        else:
            await ctx.message.reply("I ain't connected to a vc!")

    # METHODS

    async def stop_conversation(self, channel):
        if channel.type is discord.ChannelType.private:
            logger.info(
                f"Ending convo in DM with {channel.recipient if channel.recipient else 'unknown user'}")
        else:
            logger.info(f"Ending convo in {channel.name}")
        self.bot_brain.currentConversations[channel.id] = None

    async def replyToMessage(self, message, conversation=None):
        logger.info("Responding")
        if not conversation:
            conversation = self.bot_brain.create_conversation(message.channel)
        conversation.responding_task = asyncio.create_task(self.bot_brain.reply(message, conversation))

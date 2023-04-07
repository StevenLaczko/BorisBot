import datetime
import json
import os
import random
from enum import Enum, auto
from typing import Union

import discord
import pytz
from discord.ext import commands

import src.cogs.NLPResponder.GPTAPI as GPTAPI
import src.helpers.StringMatchHelp as StringMatchHelp
from src.cogs.NLPResponder.BotBrain import BotBrain
from src.cogs.NLPResponder.BotResponse import BotResponse
from src.cogs.NLPResponder.Conversation import Conversation
from src.cogs.NLPResponder.Context import Context
from src.helpers import DiscordBot
from src.helpers.logging_config import logger


class ARGS(Enum):
    WEIGHTS = "weights"
    PROB_MIN = "probMin"
    DEBUG_CHANNEL_ID = "debugChannelId"
    ENABLE_AUTO_WEIGHTS = "enableAutoWeights"
    CONTEXT_LEN = "contextLen"


class STATES(Enum):
    NOMINAL = auto()
    AWAITING_INPUT = auto()


SPLIT_CHAR = '\t'
ADMIN_ROLE_ID = 658116626712887316
PROB_MIN_DEF = 0.7
WEIGHTS_DEF = [1.2, 0.7, 1.1, 1]
CONTEXT_LEN_DEF = 5
GOOD_VOTE = "good"
BAD_VOTE = "bad"
SETTINGS_FILE = "learned_reply_settings"
MAX_CONTEXT_WORDS = 100
MAX_CONVO_WORDS = 200
MEMORY_CHANCE = 1
CONVO_END_DELAY = datetime.timedelta(minutes=3)
ADD_COMMAND_REACTIONS = True
RESPONSE_FILENAME = "responses.txt"
MEMORY_FILENAME = "memories.json"


# TODO Add undo (at least to addResponse)
class Respondtron(commands.Cog):
    responseFilePath = ""
    botNoResponse = ""
    cmdErrorResponse = "I do believe you messed up the command there, son."
    learned_reply_settings = {ARGS.WEIGHTS: WEIGHTS_DEF, ARGS.PROB_MIN: PROB_MIN_DEF, ARGS.DEBUG_CHANNEL_ID: None,
                              ARGS.ENABLE_AUTO_WEIGHTS: False, ARGS.CONTEXT_LEN: CONTEXT_LEN_DEF}
    lastScores = ()
    lastRated = False

    # to prompt user when adding new response
    tempArgs = None
    state = STATES.NOMINAL

    def __init__(self, bot: DiscordBot.DiscordBot, prefix, responseFile=RESPONSE_FILENAME, botNoResponse="", args=None,
                 memoryFilename=MEMORY_FILENAME):
        self.bot = bot
        self.prefix: str = prefix
        self.memoryFilePath = DiscordBot.getFilePath(memoryFilename)
        self.botBrain = BotBrain()

        # load memories
        if os.path.isfile(self.memoryFilePath):
            with open(self.memoryFilePath, 'r') as memoryFile:
                self.memory: list[str] = json.loads(memoryFile.read())

    # EVENTS

    # on_message listens for incoming messages starting with an @(botname) and then responds to them
    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        current_convo = None
        if message.channel.id in self.botBrain.currentConversations:
            current_convo = self.botBrain.currentConversations[message.channel.id]

        # consider conversations over after 3 minutes of boris not responding
        conversationsToStop = []
        now = datetime.datetime.now()
        for c in self.botBrain.currentConversations:
            if not self.botBrain.currentConversations[c]:
                continue
            dt = CONVO_END_DELAY
            if self.botBrain.currentConversations[c].timestamp + dt < now:
                channel = self.botBrain.currentConversations[c].channel
                if not channel:
                    logger.error(f"Conversation does not have channel attribute")
                else:
                    conversationsToStop.append(channel)

        if message.author.id == self.bot.user.id:
            return

        if message.clean_content.strip()[0] != self.prefix:
            await self.handle_response_situations(message, current_convo)

        for c in conversationsToStop:
            await self.stopConversation(c)

    async def handle_response_situations(self, message, conversation):
        mention_ids = [m.id for m in message.mentions]
        if "boris stop" in message.clean_content.lower():
            await self.stopConversation(message.channel)
        elif isinstance(message.channel, discord.DMChannel):
            logger.info("Received message in DM")
            await self.replyToMessage(message)
        elif self.bot.user.id in mention_ids:
            logger.warning(self.bot.user.name + " mention DETECTED")
            await self.replyToMessage(message, conversation)
        elif "boris" in message.clean_content.lower():
            logger.warning("I heard my name.")
            if self.botBrain.isMessageInConversation(message) or 0.2 > random.random():
                await self.replyToMessage(message, conversation)
        elif self.botBrain.isMessageInConversation(message):
            logger.warning("Message received in convo channel")
            self.botBrain.currentConversations[message.channel.id].timestamp = datetime.datetime.now()
            if 0.3 > random.random():
                await self.replyToMessage(message, conversation)
        # TODO 5% chance asks GPT if it's relevant to Boris or his memories
        elif 0.05 > random.random():
            await self.replyToMessage(message, conversation)

    async def stopConversation(self, channel):
        logger.info(f"{CONVO_END_DELAY} passed. Ending convo in {channel.name}")
        self.botBrain.currentConversations[channel.id] = None
        if MEMORY_CHANCE > random.random():
            context = await self.getConvoContext(channel, after=None, ignore_list=self.bot.settings["ignore_list"])
            await self.botBrain.storeMemory("main", self.bot, context)
            await self.botBrain.setMood("main", GPTAPI.getMood(self.bot, context, self.botBrain.getMemoryPool("main"),
                                                               self.bot.settings["id_name_dict"]))

    # COMMANDS

    @commands.command(name="remember", help="Remember.")
    @commands.is_owner()
    async def remember(self, ctx):
        await self.storeMemory(
            await self.getConvoContext(ctx.channel, after=None, ignore_list=self.bot.settings["ignore_list"]))

    # METHODS

    async def stopConversation(self, channel):
        if channel.type is discord.ChannelType.private:
            logger.info(
                f"{CONVO_END_DELAY} passed. Ending convo in DM with {channel.recipient if channel.recipient else 'unknown user'}")
        else:
            logger.info(f"{CONVO_END_DELAY} passed. Ending convo in {channel.name}")

        self.botBrain.currentConversations[channel.id] = None
        if MEMORY_CHANCE > random.random():
            context = await self.getConvoContext(channel, after=None, ignore_list=self.bot.settings["ignore_list"])
            await self.storeMemory(context)
            await self.setMood(context)

    async def getContext(self, channel, before, after=False, num_messages_requested=None,
                         max_context_words=None, ignore_list=None):
        if not max_context_words:
            max_context_words = self.bot.settings["max_context_words"]
            if not max_context_words:
                max_context_words = MAX_CONTEXT_WORDS
        logger.info("Getting context")
        all_messages = []
        now = datetime.datetime.now(tz=pytz.UTC)
        if num_messages_requested is None:
            num_messages_requested = self.bot.settings["num_messages_per_request"]
        if after is False:
            past_cutoff = now - datetime.timedelta(minutes=30)
            after = past_cutoff
        # Keep getting messages until the word count reach 100
        word_count = 0
        do_repeat = True
        while do_repeat:
            messages: list[discord.Message] = []
            async for m in channel.history(limit=num_messages_requested, after=after, before=before,
                                           oldest_first=False):
                if ignore_list and m.author.id in ignore_list:
                    continue
                messages.append(m)
                word_count += len(m.clean_content.split())
            if len(messages) > 0:
                before = messages[-1]

            all_messages.extend(messages)
            if word_count > max_context_words or len(messages) < num_messages_requested:
                do_repeat = False

        logger.info(f"Number of messages looked at: {len(all_messages)}")
        logger.info(f"Word count: {word_count}")
        all_messages.reverse()
        return all_messages

    async def getConvoContext(self, channel, before=False,
                              after: Union[discord.Message, datetime.datetime, None, bool] = False,
                              max_context_words=None, ignore_list=None):
        if not max_context_words:
            max_context_words = self.bot.settings["max_context_words"]
            if not max_context_words:
                max_context_words = MAX_CONTEXT_WORDS
        context = []
        try:
            message: discord.Message = [m async for m in channel.history(limit=2)][1]  # second to last message to start
        except IndexError as e:
            logger.error("Not enough messages in channel to get context.")
            logger.error(e)
            return []
        if before is False:
            before = message.created_at + datetime.timedelta(minutes=5)
        try:
            context = await self.getContext(channel, before=before, after=after,
                                            max_context_words=max_context_words, ignore_list=ignore_list)
        except Exception as e:
            logger.error(e)
        return context

    async def saveMemory(self, _memory, shrink=True, _explain=True):
        for m in self.memory:
            isMatch, probability = await self.botMatchString(m, _memory)
            if probability > 0.85:
                close = m
                logger.info(f"Not saving memory. Too close to {close}, probability {probability}")
                return

        local_tz = pytz.timezone("America/New_York")
        local_timestamp = datetime.datetime.now(local_tz)
        ts = local_timestamp.strftime(GPTAPI.DATETIME_FSTRING)
        _memory = f"[{ts}] {_memory}"
        logger.info(f"Saving new memory: {_memory}")
        self.memory.append(_memory.lower())
        if shrink:
            self.memory = GPTAPI.organizeMemories(self.memory, self.bot.settings["max_context_words"], explain=_explain)
        with open(self.memoryFilePath, 'w+') as memoryFile:
            (json.dump(self.memory, memoryFile, indent=0))

    async def storeMemory(self, conversation_log):
        _memory = GPTAPI.rememberGPT(self.bot, conversation_log, self.bot.settings["id_name_dict"], memory=self.memory)
        if _memory != "" and _memory is not None:
            logger.info(f"Storing memory `{_memory}")
            await self.saveMemory(_memory)
        else:
            logger.info(f"Storing no memories from conversation of length {len(conversation_log)}")

    async def setMood(self, conversation_log):
        self.mood = GPTAPI.getMood(self, conversation_log, self.memory, self.bot.settings["id_name_dict"])
        logger.info(f"Setting mood from convo to {self.mood}")

    async def parseGPTResponse(self, bot_response: BotResponse):
        return bot_response.response_str if bot_response.response_str else ""

    # pool is a memory pool. It can be a string for one pool, or a list of pools
    async def replyGPT(self, message, conversation: Conversation, max_context_words=None, _memory=None, _mood=None):
        cstack = conversation.context_stack
        if not max_context_words:
            max_context_words = self.bot.settings["max_context_words"]
            if not max_context_words:
                max_context_words = MAX_CONTEXT_WORDS
        if not _memory:
            _memory = cstack.get_memories()
        if not _mood:
            _mood = conversation.mood
        chatlog_context = await self.getContext(message.channel, message, max_context_words=max_context_words)
        async with message.channel.typing():
            bot_response: BotResponse = await GPTAPI.getGPTResponse(self.bot, message, chatlog_context, True,
                                                                    self.botBrain.currentConversations[
                                                                        message.channel.id],
                                                                    self.bot.settings["id_name_dict"],
                                                                    memory=_memory, mood=_mood)
        if bot_response.response_str:
            logger.info(f"Response: {bot_response.response_str}")
            msg = await message.channel.send(bot_response.response_str)
            self.botBrain.currentConversations[message.channel.id].bot_messageid_response[
                msg.id] = bot_response.full_response
        if bot_response.new_memory:
            if ADD_COMMAND_REACTIONS:
                await message.add_reaction('🤔')
            await self.botBrain.saveMemory(cstack, bot_response.new_memory)
        if bot_response.new_mood:
            if ADD_COMMAND_REACTIONS:
                await message.add_reaction('☝')
            self.botBrain.set_mood(bot_response.new_mood)

    async def replyToMessage(self, message, conversation):
        logger.info("Responding")
        context = conversation.context if conversation else "main"
        if not self.botBrain.isMessageInConversation(message):
            self.botBrain.currentConversations[message.channel.id] = Conversation(message.channel, context,
                                                                                  timestamp=datetime.datetime.now())
        await self.replyGPT(message, conversation)

    async def botMatchString(self, str1, str2):
        args = StringMatchHelp.fuzzyMatchString(str1, str2, self.learned_reply_settings[ARGS.WEIGHTS],
                                                self.learned_reply_settings[ARGS.PROB_MIN])
        self.lastScores = args[2]
        if args[3] is not None:
            logger.info(args[2])
        return args[0:2]
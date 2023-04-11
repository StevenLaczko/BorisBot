import datetime
import json
import os
from typing import Union

import RunBoris
from src.helpers.logging_config import logger

import discord
import pytz

from src.helpers import DiscordBot
from src.helpers.BotResponse import BotResponse
from src.helpers.Conversation import Conversation
import re
import sys
import src.helpers.GPTAPI as GPTAPI
import src.helpers.StringMatchHelp as StringMatchHelp
from discord.ext import commands
from enum import Enum, auto
import random
import pickle



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
MEMORY_CHANCE = 0
CONVO_END_DELAY = datetime.timedelta(hours=1)
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
        self.responseFilePath = DiscordBot.getFilePath(responseFile)
        self.memoryFilePath = DiscordBot.getFilePath(memoryFilename)
        self.botNoResponse = botNoResponse
        self.loadLearnedReplySettings(args)
        self.currentConversations: dict[int, Conversation] = {}
        self.memory: list[str] = []
        self.mood: str = ""  # mood

        # load memories
        if os.path.isfile(self.memoryFilePath):
            with open(self.memoryFilePath, 'r') as memoryFile:
                self.memory: list[str] = json.loads(memoryFile.read())

        # create backup of responses
        logger.warning("Backing up response file")
        with open(self.responseFilePath, 'r') as responses:
            with open(self.responseFilePath, 'w+') as backup:
                backup.write(responses.read())

    # SETTERS

    def setWeights(self, weights):
        self.learned_reply_settings[ARGS.WEIGHTS] = weights

    def setAutoWeights(self, isEnabled):
        self.learned_reply_settings[ARGS.ENABLE_AUTO_WEIGHTS] = isEnabled

    def setProbMin(self, probMin):
        self.learned_reply_settings[ARGS.PROB_MIN] = probMin

    def setDebugChannel(self, id):
        self.learned_reply_settings[ARGS.DEBUG_CHANNEL_ID] = id

    def loadLearnedReplySettings(self, args):
        if args is not None:
            for iArg in args:
                if iArg in ARGS:
                    if iArg == ARGS.WEIGHTS:
                        self.setWeights(args[iArg])
                    elif iArg == ARGS.PROB_MIN:
                        self.setProbMin(args[iArg])
                    elif iArg == ARGS.DEBUG_CHANNEL_ID:
                        self.setDebugChannel(args[iArg])
                    elif iArg == ARGS.ENABLE_AUTO_WEIGHTS:
                        self.setAutoWeights(args[iArg])

    def saveSettings(self, settings, file):
        save_obj(settings, file)
        logger.info(f"Saved Settings: {settings}")

    # EVENTS

    # on_message listens for incoming messages starting with an @(botname) and then responds to them
    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        conversationsToStop = []
        # consider conversations over after 3 minutes of boris not responding
        now = datetime.datetime.now()
        for c in self.currentConversations:
            if not self.currentConversations[c]:
                continue
            dt = CONVO_END_DELAY
            if self.currentConversations[c].timestamp + dt < now:
                channel = self.currentConversations[c].channel
                if not channel:
                    logger.error(f"Conversation does not have channel attribute")
                else:
                    conversationsToStop.append(channel)

        botID = self.bot.user.id
        if message.author.id == botID:
            return

        # Boris responding to messages when he was waiting for input from someone
        # TODO allow multiple users to do this at once. Currently only allows one, as it uses tempArgs[0] for the user's name
        if self.state == STATES.AWAITING_INPUT and message.author == self.tempArgs[0]:
            # If the trigger/response was correct, add the response
            if message.content == "y":
                self.addTempResponse(self.tempArgs)
                self.state = STATES.NOMINAL
                await message.add_reaction('✅')
            elif message.content == "n":
                await message.add_reaction('❌')
                self.state = STATES.NOMINAL

        if message.clean_content.strip()[0] != self.prefix:
            await self.handle_response_situations(message)

        for c in conversationsToStop:
            await self.stopConversation(c)


    async def handle_response_situations(self, message):
        mention_ids = [m.id for m in message.mentions]
        if "boris stop" in message.clean_content.lower():
            await self.stopConversation(message.channel)
        elif isinstance(message.channel, discord.DMChannel):
            logger.info("Received message in DM")
            await self.replyToMessage(message)
        elif self.bot.user.id in mention_ids:
            logger.warning(self.bot.user.name + " mention DETECTED")
            await self.replyToMessage(message)
        elif "boris" in message.clean_content.lower():
            logger.warning("I heard my name.")
            if (message.channel.id in self.currentConversations and self.currentConversations[
                message.channel.id]) or 0.2 > random.random():
                await self.replyToMessage(message)
        elif message.channel.id in self.currentConversations and self.currentConversations[message.channel.id]:
            logger.warning("Message received in convo channel")
            self.currentConversations[message.channel.id].timestamp = datetime.datetime.now()
            if 0.3 > random.random():
                await self.replyToMessage(message)
        # TODO 5% chance asks GPT if it's relevant to Boris or his memories
        elif 0.02 > random.random():
            await self.replyToMessage(message)

    # COMMANDS

    @commands.command(name='teach', help='Usage: ~teach \"Trigger phrase\" \"Desired response\"')
    async def teach(self, ctx, *args):
        # take in and sanitize trigger
        iterargs = iter(args)
        trigger = str(next(iterargs))
        logger.info("Trigger: " + trigger)
        trigger = re.sub(r'[^a-zA-Z ]', '', str(trigger).strip().lower())

        response = str(next(iterargs)) + ' '
        for arg in iterargs:
            logger.info("Arg: " + str(arg))
            response += str(arg) + ' '
        response = response.strip()

        if await self.addResponse(ctx, self.responseFilePath, trigger, response) is False:
            await ctx.send("I've already learned that, friend!")

    @commands.command(name="setProb", help="Usage: ~setProb [0.0-1.0]\nSets the sensitivity for matching triggers.",
                      hidden=True)
    async def setProbCommand(self, ctx, prob):
        if ctx.channel.get_role(ADMIN_ROLE_ID) in ctx.message.author.roles:
            await self.setProb(prob)
            return

    @commands.command(name="setWeights", hidden=True)
    async def setWeightCommand(self, ctx, *weights):
        if ctx.channel.get_role(ADMIN_ROLE_ID) in ctx.message.author.roles:
            # convert weights to floats
            floatWeights = []
            for i in range(len(weights)):
                floatWeights.append(float(weights[i].strip(", ")))

            logger.info(f"Weight list: {floatWeights}")

            try:
                self.setWeights(floatWeights)
                await ctx.send("Weights set to " + str(floatWeights))
            except TypeError:
                logger.error(sys.exc_info())
                await ctx.send("Bad input, bud. Comma separated and between 0 and 1, please.")
            return

    @commands.command(name="saveSettings", hidden=True)
    async def saveSettingsCommand(self, ctx):
        if ctx.channel.get_role(ADMIN_ROLE_ID) in ctx.message.author.roles:
            self.saveSettings(self.learned_reply_settings, SETTINGS_FILE)
            await ctx.send("Setting's saved. Turnin' the heat up. Keepin' em nice and cozy.")
            return

    @commands.command(name="rate", help="Rate Boris' response for accuracy.\nUsage: ~rate [good/bad]")
    async def rateResponse(self, ctx, rating):
        rating = str(rating).lower().strip()
        isGood = None

        # if the last response was already rated, return
        if self.lastRated:
            return

        if rating == GOOD_VOTE:
            isGood = True
        elif rating == BAD_VOTE:
            isGood = False
        else:
            await ctx.send(self.cmdErrorResponse)
            return

        self.alterWeights(isGood)
        self.lastRated = True
        await ctx.send("Response rated. Gimme time, I'm learnin'.")

    @commands.command(name="weights", help="Sends weights as a message", hidden=True)
    async def weightsCommand(self, ctx):
        await ctx.send(self.learned_reply_settings[ARGS.WEIGHTS])

    @commands.command(name="remember", help="Remember.")
    @commands.is_owner()
    async def remember(self, ctx):
        await self.storeMemory(await self.getConvoContext(ctx.channel, after=None, ignore_list=self.ignore_list), self.bot.settings["id_name_dict"])



    # METHODS

    async def stopConversation(self, channel):
        if channel.type is discord.ChannelType.private:
            logger.info(f"{CONVO_END_DELAY} passed. Ending convo in DM with {channel.recipient if channel.recipient else 'unknown user'}")
        else:
            logger.info(f"{CONVO_END_DELAY} passed. Ending convo in {channel.name}")


        self.currentConversations[channel.id] = None
        if MEMORY_CHANCE > random.random():
            context = await self.getConvoContext(channel, after=None, ignore_list=self.bot.settings["ignore_list"])
            await self.storeMemory(context)
            await self.setMood(context)

    def resetState(self):
        self.state = STATES.NOMINAL
        self.tempArgs = []

    # if user vote was good, increase weight of highest string matching factor
    # if vote was bad, decrease weight of lowest string matching factor
    def alterWeights(self, isGood):
        # find the largest string matching factor
        weights = self.learned_reply_settings[ARGS.WEIGHTS]
        if isGood:
            largestWeight = 0
            iLargestWeight = 0
            for i in range(len(weights)):
                if weights[i] > largestWeight:
                    largestWeight = weights[i]
                    iLargestWeight = i

            # increase weight of highest string matching factor
            logger.info(f"Weight index changed: {iLargestWeight}")
            logger.info(f"Change from: {weights[iLargestWeight]}")
            weights[iLargestWeight] += 0.1
            logger.info(f"To: {weights[iLargestWeight]}")

        elif not isGood:
            smallestWeight = 0
            iSmallestWeight = 0
            # find the largest string matching factor
            for i in range(len(weights)):
                if weights[i] < smallestWeight:
                    smallestWeight = weights[i]
                    iSmallestWeight = i

            # lower weight of lowest string matching factor
            logger.info(f"Weight index changed: {smallestWeight}")
            logger.info(f"Change from: {weights[iSmallestWeight]}")
            weights[iSmallestWeight] -= 0.1
            logger.info(f"To: {weights[iSmallestWeight]}")

        self.learned_reply_settings[ARGS.WEIGHTS] = weights

    async def addResponse(self, ctx, responseFile, newTrigger, newResponse):
        triggerMatch = False
        duplicate = False
        matchedTrigger = ""
        with open(responseFile, 'r') as responses:
            lines = responses.readlines()

        for i in range(len(lines)):  # iterate through triggers and responses
            entries = lines[i].split(SPLIT_CHAR)
            trigger = entries[0]

            # TODO Make this find all matches and choose the highest probability
            # if the trigger is already present, add new response to trigger
            matchArgs = await self.botMatchString(trigger, newTrigger)
            if matchArgs[0]:
                for response in entries:  # skip if response is already present
                    if newResponse.lower().strip() == response.lower().strip():
                        duplicate = True

                triggerMatch = True
                if not duplicate:
                    matchedTrigger = trigger
                    lines[i] = lines[i].strip()
                    lines[i] += SPLIT_CHAR + newResponse

        # Adding Response

        if duplicate:
            logger.info("Duplicate Response. Not adding.")
            return False

        # Add response to existing trigger
        elif triggerMatch:
            self.prepPrompt(ctx.message.author, lines)
            await ctx.send("Adding response to existing trigger \"" + matchedTrigger + "\"\nIs this correct? (y/n)")
            return True
        # if the trigger was not in the file before, make a new trigger+response
        else:
            self.prepPrompt(ctx.message.author, newTrigger, newResponse)
            await ctx.send(
                "Adding new trigger/response \"" + newTrigger + "\"/\"" + newResponse + "\"\nIs this correct? (y/n)")
            return True

    def prepPrompt(self, *args):
        self.tempArgs = []
        for arg in args:
            self.tempArgs.append(arg)
        self.state = STATES.AWAITING_INPUT

    def addTempResponse(self, args):
        if len(args) == 3:
            newTrigger = args[1]
            newResponse = args[2]
            with open(self.responseFilePath, 'a') as responses:
                logger.info("Adding new trigger/response.\n Trigger: " + newTrigger)
                responses.write(newTrigger + SPLIT_CHAR + newResponse + "\n")

        elif len(args) == 2:
            lines = self.tempArgs[1]
            with open(self.responseFilePath, 'w') as responses:
                logger.info("Added response to existing trigger")
                responses.write(''.join(lines))

    async def searchMessages(self, searchTerm):
        # TODO idea
        # Ask GPT for a rating from 0-100 for if we should search for a term,
        # or just trigger when "said" is in a message,
        # then search the server for the term, and give it to Boris (in a memory) for extra response context.
        pass

    async def getContext(self, channel, before, after: Union[bool, None] = False, num_messages_requested=None,
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
                if word_count > max_context_words:
                    break
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

        #local_tz = pytz.timezone("America/New_York")
        #local_timestamp = datetime.datetime.now(local_tz)
        #ts = local_timestamp.strftime(GPTAPI.DATETIME_FSTRING)
        _memory = f"{_memory}"
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

    async def replyGPT(self, message, max_context_words=None, _memory=None, _mood=None):
        if not max_context_words:
            max_context_words = self.bot.settings["max_context_words"]
            if not max_context_words:
                max_context_words = MAX_CONTEXT_WORDS
        if not _memory:
            _memory = self.memory
        if not _mood:
            _mood = self.mood
        context = await self.getContext(message.channel, message, max_context_words=max_context_words, after=None)
        async with message.channel.typing():
            bot_response: BotResponse = await GPTAPI.getGPTResponse(self.bot, message, context, True,
                                                                    self.currentConversations[message.channel.id],
                                                                    self.bot.settings["id_name_dict"],
                                                                    memory=_memory, mood=_mood)
            if bot_response.response_str:
                logger.info(f"Response: {bot_response.response_str}")
                msg = await message.channel.send(bot_response.response_str)
                self.currentConversations[message.channel.id].bot_messageid_response[msg.id] = bot_response.full_response
        if bot_response.new_memory:
            if ADD_COMMAND_REACTIONS:
                await message.add_reaction('🤔')
            await self.saveMemory(bot_response.new_memory)
        if bot_response.new_mood:
            logger.info(f"New mood: {bot_response.new_mood}")
            if ADD_COMMAND_REACTIONS:
                await message.add_reaction('☝')
            self.mood = bot_response.new_mood

    async def replyToMessage(self, message: discord.Message):
        logger.info("Responding")
        if message.channel.id not in self.currentConversations or not self.currentConversations[message.channel.id]:
            self.currentConversations[message.channel.id] = Conversation(message.channel, timestamp=datetime.datetime.now())
        else:
            self.currentConversations[message.channel.id].timestamp = datetime.datetime.now()
        # get trigger
        message_string = message.clean_content.strip()
        triggerList = message_string.split()[1:]
        trigger = ""
        for word in triggerList:
            trigger += word + ' '
        trigger = StringMatchHelp.sanitize_string(trigger)

        # open file of responses
        with open(self.responseFilePath, 'r') as f:
            lines = f.readlines()

        matches = []
        # iterate for the number of words in the trigger
        for line in lines:
            lineEntries = line.split(SPLIT_CHAR)
            lineTrigger = lineEntries[0]

            matchArgs = await self.botMatchString(trigger, lineTrigger)
            # add new response to trigger
            # if the trigger is matched, add it to the matches list
            if matchArgs[0]:
                matches.append((lineEntries, matchArgs[1]))  # save the chopped up line and the match probability

        response = ""
        logger.info(f"Matches: {matches}")
        # if there are any matches, choose the one with the highest probability
        if len(matches) > 0:
            highestMatch = matches[0]
            for match in matches:
                # if line is higher probability than saved match, replace
                if match[1] > highestMatch[1]:
                    highestMatch = match

            # get random response from list
            responses = highestMatch[0][1:]
            response = random.choice(responses)
            logger.info("Response: " + response)
            await message.channel.send(response)
        else:
            await self.replyGPT(message)
            return

    async def botMatchString(self, str1, str2):
        args = StringMatchHelp.fuzzyMatchString(str1, str2, self.learned_reply_settings[ARGS.WEIGHTS], self.learned_reply_settings[ARGS.PROB_MIN])
        self.lastScores = args[2]
        if args[3] is not None:
            logger.info(args[2])
        return args[0:2]


def save_obj(obj, name):
    with open('obj/' + name + '.pkl', 'wb+') as f:
        pickle.dump(obj, f, pickle.DEFAULT_PROTOCOL)


def load_obj(name):
    with open('obj/' + name + '.pkl', 'rb') as f:
        return pickle.load(f)

import pickle
import random
import re
import sys
from enum import Enum, auto

import discord
from discord.ext import commands

import src.helpers.StringMatchHelp as StringMatchHelp
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
RESPONSE_FILENAME = "responses.txt"


# TODO Add undo (at least to addResponse)
class Respondtron(commands.Cog):
    cmdErrorResponse = "I do believe you messed up the command there, son."
    learned_reply_settings = {ARGS.WEIGHTS: WEIGHTS_DEF, ARGS.PROB_MIN: PROB_MIN_DEF, ARGS.DEBUG_CHANNEL_ID: None,
                              ARGS.ENABLE_AUTO_WEIGHTS: False, ARGS.CONTEXT_LEN: CONTEXT_LEN_DEF}
    lastScores = ()
    lastRated = False

    # to prompt user when adding new response
    tempArgs = None
    state = STATES.NOMINAL

    def __init__(self, bot: DiscordBot.DiscordBot, responseFile=RESPONSE_FILENAME, botNoResponse="", args=None):
        self.bot = bot
        self.responseFilePath = DiscordBot.getFilePath(responseFile)
        self.botNoResponse = botNoResponse
        self.loadLearnedReplySettings(args)

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

        if self.bot.user in message.mentions:
            await self.getLearnedReply(message)
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

    # METHODS

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

    async def getLearnedReply(self, message):
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
            logger.info("Response: " + response)
            await message.reply(response)

    async def botMatchString(self, str1, str2):
        args = StringMatchHelp.fuzzyMatchString(str1, str2, self.learned_reply_settings[ARGS.WEIGHTS],
                                                self.learned_reply_settings[ARGS.PROB_MIN])
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

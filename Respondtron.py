from fuzzywuzzy import fuzz
import re
import discord
from discord.ext import commands
from fuzzywuzzy import process
import random

SPLIT_CHAR = '\t'
PARTIAL_RATIO_MIN = 70
RATIO_MIN = 60
TOKEN_SET_MIN = 70
TOKEN_SORT_MIN = 70
PROB_MIN = 0.7


class Respondtron(commands.Cog):
    responseFile = ""
    botNoResponse = ""

    def __init__(self, bot, responseFile, botNoResponse, weights=(1.2, 0.7, 1.1, 1), probMin=0.7):
        self.bot = bot
        self.responseFile = responseFile
        self.botNoResponse = botNoResponse
        self.weights = weights
        self.probMin = probMin

    # on_message listens for incoming messages starting with an @(botname) and then response to them
    @commands.Cog.listener()
    async def on_message(self, message):
        mentionIDList = []
        for mention in message.mentions:
            mentionIDList.append(mention.id)
        botID = self.bot.user.id
        if botID in mentionIDList:
            print(self.bot.user.name + " mention DETECTED")

            # get and send response
            response = await self.getResponse(self.responseFile, message)
            if response is not None:
                print("Response: " + response)
                await message.channel.send(response)
            else:
                await message.channel.send(self.botNoResponse)

    # teach
    # teach allows the bot to learn new trigger/response pairs
    @commands.command(name='teach', help='Usage: ~teach \"Trigger phrase\" \"Desired response\"')
    async def teach(self, ctx, *args):
        # take in and sanitize trigger
        iterargs = iter(args)
        trigger = str(next(iterargs))
        print("Trigger: " + trigger)
        trigger = re.sub(r'[^a-zA-Z ]', '', str(trigger).strip().lower())

        response = str(next(iterargs)) + ' '
        for arg in iterargs:
            print("Arg: " + str(arg))
            response += str(arg) + ' '
        response = response.strip()
        print("Learning to respond to \"" + trigger + "\" with \"" + response + '\"')
        await ctx.send("Learned to respond to \"" + trigger + "\" with \"" + response + '\"')

        await self.addResponse(self.responseFile, trigger, response)

    async def addResponse(self, responseFile, newTrigger, newResponse):
        triggerMatch = False
        with open(responseFile, 'r') as responses:
            lines = responses.readlines()

        for i in range(len(lines)):
            words = lines[i].split(SPLIT_CHAR, 1)
            trigger = words[0]

            # add new response to trigger
            if self.fuzzyMatchString(trigger, newTrigger, self.weights, self.probMin)[0]:
                lines[i] = lines[i].strip()
                lines[i] += SPLIT_CHAR + newResponse + '\n'
                triggerMatch = True

        if triggerMatch:
            with open(responseFile, 'w') as responses:
                responses.write(''.join(lines))
                print("Added response to existing trigger \"" + newTrigger + "\"")
        else:  # if the trigger was not in the file before, make a new trigger+response
            with open(responseFile, 'a') as responses:
                responses.write('\n' + newTrigger + SPLIT_CHAR + newResponse)
                print("Added new trigger/response \"" + newTrigger + "\"/\"" + newResponse + "\"")

    async def getResponse(self, responseFile, message):
        # get trigger
        triggerList = str(message.content).split()[1:]
        trigger = ""
        for word in triggerList:
            trigger += word + ' '
        trigger = sanitize_string(trigger)

        # open file of responses
        with open(responseFile, 'r') as responseFile:
            lines = responseFile.readlines()

        # iterate for the number of words in the trigger
        for i in range(len(trigger.split())):
            for line in lines:
                entries = line.split(SPLIT_CHAR)
                lineTrigger = entries[0]

                # add new response to trigger
                if fuzzyMatchString(trigger, lineTrigger, self.weights, self.probMin)[0]:
                    responses = entries[1:]
                    response = random.choice(responses)
                    return response

        return self.botNoResponse


def sanitize_string(input):
    return re.sub(r'[^a-zA-Z ]', '', str(input).strip().lower())


# match strings with fuzzywuzzy
def fuzzyMatchString(str1, str2, weights, probMin):
    partialRatio = fuzz.partial_ratio(str1, str2)
    tokenSetRatio = fuzz.token_set_ratio(str1, str2)
    tokenSortRatio = fuzz.token_sort_ratio(str1, str2)
    ratio = fuzz.ratio(str1, str2)
    partialTokenSetRatio = fuzz.partial_token_set_ratio(str1, str2)
    partialTokenSortRatio = fuzz.partial_token_sort_ratio(str1, str2)

    scores = [ratio, partialRatio, tokenSetRatio, tokenSortRatio]

    sumScores = 0
    for i in range(len(scores)):
        sumScores += (scores[i] / 100) * weights[i]

    probability = sumScores / len(scores)

    isMatch = False
    if probability > probMin:
        isMatch = True

    print("Analysis of \"", str1, "\" with \"", str2, "\" \n",
          "Matched? ", isMatch, "\n",
          "Partial ratio: ", partialRatio, "\n",
          "Ratio: ", ratio, "\n",
          "Token set ratio: ", tokenSetRatio, "\n",
          "Token sort ratio: ", tokenSortRatio, "\n",
          "Partial token set ratio: ", partialTokenSetRatio, "\n",
          "Partial token sort ratio: ", partialTokenSortRatio, "\n",
          "Probability: ", probability)

    return isMatch, partialRatio, ratio  # return tuple of values

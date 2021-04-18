import inspect

import discord
import discord.ext.tasks
# import GPT_Test
import re
import random
from discord.ext import commands
import subprocess
import os
from textwrap import dedent

import Respondtron
import ReminderCog
import MemeGrabber
import BorisCommands
import StringMatchHelp

TOKEN_FILE = ".token"
BOT_PREFIX = ('<@698354966078947338>', '<@!698354966078947338>', '<@&698361022712381451>')
BOT_FUZZY_PREFIX = ('~')
STR_NO_RESPONSE = "Look, I'm not all that bright. \nType ~help teach and teach me some new phrases, would ya?"
botDict = 'responses.txt'
botNoResponse = "Use ~teach \"Trigger\" \"Response\" to teach me how to respond to something!"
WEIGHTS = [1.2, 0.7, 1.1, 1]
PROB_MIN = 0.7
PLAN_REACTIONS = ['🇫', '🇸', '🌞', '❌']
COMMAND_CLASSES = (Respondtron.Respondtron, ReminderCog.ReminderCog, MemeGrabber.MemeGrabber)

if __name__ == '__main__':
    with open(TOKEN_FILE, 'r') as tokenFile:
        TOKEN = tokenFile.read()

    client = discord.Client()
    bot = commands.Bot(command_prefix=BOT_PREFIX)

    args = {Respondtron.ARGS.WEIGHTS: WEIGHTS,
            Respondtron.ARGS.PROB_MIN: PROB_MIN,
            Respondtron.ARGS.DEBUG_CHANNEL_ID: 696863794743345152,
            Respondtron.ARGS.ENABLE_AUTO_WEIGHTS: True}

    respTron = Respondtron.Respondtron(bot, botDict, botNoResponse)
    bot.add_cog(respTron)

    remindCog = ReminderCog.ReminderCog(bot)
    bot.add_cog(remindCog)

    memeGrabber = MemeGrabber.MemeGrabber(bot)
    bot.add_cog(memeGrabber)

    borisCommands = BorisCommands.BorisCommands(bot)
    bot.add_cog(borisCommands)

    # mafiaCog = MafiaCog.Mafia(bot, None, None)
    # bot.add_cog(mafiaCog)

    # gptTest = GPT_Test.GPT_Test(bot)
    # bot.add_cog(gptTest)

    bot.run(TOKEN)

import discord
import discord.ext.tasks
#import GPT_Test
import re
import random 
from discord.ext import commands
import subprocess
import os
from textwrap import dedent

import Respondtron
import MafiaCog
import ReminderCog
import MemeGrabber

TOKEN_FILE = ".token"
BOT_PREFIX = ('<@698354966078947338>', '~', '<@!698354966078947338>', '<@&698361022712381451>')
STR_NO_RESPONSE = "Look, I'm not all that bright. \nType ~help teach and teach me some new phrases, would ya?"
botDict = 'responses.txt'
botNoResponse = "Use ~teach \"Trigger\" \"Response\" to teach me how to respond to something!"
WEIGHTS = [1.2, 0.7, 1.1, 1]
PROB_MIN = 0.7
PLAN_REACTIONS = ['🇫', '🇸', '🌞', '❌']

with open(TOKEN_FILE, 'r') as tokenFile:
    TOKEN = tokenFile.read()

client = discord.Client()
bot = commands.Bot(command_prefix=BOT_PREFIX)


@bot.command(name='hi')
async def hi(ctx):
    print("Got message \'hi\'")
    greetings = ["Well howdy!",
                 "Howdy pardner!"]

    response = random.choice(greetings)
    await ctx.send(response)

@bot.command(name='output')
async def output(ctx, arg):
	with open("nohup.out", 'r') as f:
		lines = f.readlines()
		last_lines = lines[-int(arg):]
		last_lines = ''.join(last_lines)
		await ctx.send(last_lines)
		f.close()


@bot.command(name='plan', help='For planning on the weekend. You sir have to ping everyone, though.')
@commands.has_role("plannerman")
async def plan(ctx):
    print("Planning")

    msg = await ctx.send("Howdy! Les all gather up and spend some quality time together.\n"
                         "Click them emojis correspondin' to the days you're free.")
    reactions = PLAN_REACTIONS
    # reactions_names = ["regional_indicator_f", "regional_indicator_s", "sun_with_face"]
    # for reaction in reactions_names: reactions.append(discord.utils.get(bot.emojis, name=reaction))
    print(reactions)
    for dayReaction in reactions:
        if dayReaction:
            await msg.add_reaction(dayReaction)


@bot.event
async def on_ready():
    print("Boris has connected to Discord!")


@bot.event
async def on_message(message):
    print(message.content)
    if message.author == client.user:
        return

    if message.content == 'raise-exception':
        raise discord.DiscordException

    await bot.process_commands(message)


@bot.event
async def on_member_join(member):
    await send_message(658114649081774093, "<@!" + member.id + "> :gunworm:")


async def send_message(channelID, message):
    channel = bot.get_channel(channelID)
    await channel.send(message)


@bot.event
async def on_error(event, *args, **kwargs):
    with open('err.log', 'a') as f:
        if event == 'on_message':
            f.write("Unhandled message: " + str(args[0]) + "\n")
            # await send_message(696863794743345152, args[0])
        else:
            raise


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

#mafiaCog = MafiaCog.Mafia(bot, None, None)
#bot.add_cog(mafiaCog)

#gptTest = GPT_Test.GPT_Test(bot)
#bot.add_cog(gptTest)

bot.run(TOKEN)

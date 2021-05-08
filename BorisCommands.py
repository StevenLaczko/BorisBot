import inspect
import random

import discord
import discord.ext.tasks
from discord.ext import commands
import Respondtron
import StringMatchHelp
import borisbot


def fix_message(message, command):
    cmdStr = message.content
    cmdList: list = cmdStr.split()
    cmdList[0] = cmdList[0][1:]
    cmdList[0] = command
    cmdList[0] = borisbot.BOT_FUZZY_PREFIX + cmdList[0]
    message.content = ' '.join(cmdList)
    return message


class BorisCommands(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    @commands.command(name='hi')
    async def hi(self, ctx):
        print("Got message \'hi\'")
        greetings = ["Well howdy!",
                     "Howdy pardner!"]

        response = random.choice(greetings)
        await ctx.send(response)

    @commands.command(name='output')
    async def output(self, ctx, arg):
        with open("nohup.out", 'r') as f:
            lines = f.readlines()
            last_lines = lines[-int(arg):]
            last_lines = ''.join(last_lines)
            await ctx.send(last_lines)
            f.close()

    @commands.command(name='plan', help='For planning on the weekend. You sir have to ping everyone, though.')
    @commands.has_role("plannerman")
    async def plan(self, ctx):
        print("Planning")

        msg = await ctx.send("Howdy! Les all gather up and spend some quality time together.\n"
                             "Click them emojis correspondin' to the days you're free.")
        reactions = borisbot.PLAN_REACTIONS
        # reactions_names = ["regional_indicator_f", "regional_indicator_s", "sun_with_face"]
        # for reaction in reactions_names: reactions.append(discord.utils.get(bot.emojis, name=reaction))
        print(reactions)
        for dayReaction in reactions:
            if dayReaction:
                await msg.add_reaction(dayReaction)

    @commands.Cog.listener(name="on_ready")
    async def on_ready(self):
        print("Boris has connected to Discord!")

    @commands.Cog.listener(name="on_message")
    async def on_message(self, message: discord.Message):
        print(message.content)
        if message.author == self.bot.user:
            return

        if message.content == 'raise-exception':
            raise discord.DiscordException

        # for commandClass in borisbot.COMMAND_CLASSES:
        #     commandMethods = [commandClass.__dict__[method] for method in commandClass.__dict__ if
        #                       method.startswith('_') is False]
        #     for command in commandMethods:
        #         if isinstance(command, commands.core.Command):
        #             if StringMatchHelp.fuzzyMatchString(message.content, str(command))[0]:
        #                 fuzzyMessage = self.fix_message(message, str(command))
        #                 print(f"Matched command with {str(command)}.")
        #                 await self.bot.process_commands(fuzzyMessage)
        #                 return

        await self.bot.process_commands(message)

    @commands.Cog.listener("on_member_join")
    async def on_member_join(self, member):
        await self.send_message(658114649081774093, "<@!" + member.id + "> :gunworm:")

    async def send_message(self, channelID, message):
        channel = self.bot.get_channel(channelID)
        await channel.send(message)

    @commands.Cog.listener("on_error")
    async def on_error(self, event, *args, **kwargs):
        with open('err.log', 'a') as f:
            if event == 'on_message':
                f.write("Unhandled message: " + str(args[0]) + "\n")
                # await send_message(696863794743345152, args[0])
            else:
                raise


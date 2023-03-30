import os
from discord.ext import commands
import discord.ext.tasks
import discord

DATA_PATH = "data"


class DiscordBot(commands.Bot):
    def __init__(self, bot_prefix):
        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(command_prefix=bot_prefix, intents=intents)

        self.event(self.on_ready)
        self.event(self.on_error)
        self.event(self.on_command)

    async def on_command(self, ctx):
        print(f"Command: {ctx}")

    async def on_ready(self):
        print("Bot has connected to Discord!")
        await self.load_extension("src.helpers.DiscordBotCommands")

    async def add_cogs(self, cogs):
        print("Adding cogs.")
        for c in cogs:
            await self.add_cog(c)

    async def on_error(self, event, *args, **kwargs):
        print("ERROR")
        print(event)
        print(args)
        with open('err.log', 'a') as f:
            if event == 'on_message':
                f.write("Unhandled message: " + str(args[0]) + "\n")
                # await send_message(696863794743345152, args[0])
            else:
                raise

    async def send_message(self, channelID, message):
        channel = self.get_channel(channelID)
        await channel.send(message)


def getFilePath(filename):
    return os.path.join(DATA_PATH, filename)

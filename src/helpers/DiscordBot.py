from src.helpers.logging_config import logger
import os
import traceback

from discord.ext import commands
import discord.ext.tasks
import discord

DATA_PATH = "data"
EXTENSIONS = [
    "src.helpers.DiscordBotCommands"
]

os.makedirs("logs/", exist_ok=True)

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

    async def load_extensions(self, extensions):
        for e in extensions:
            if e not in self.extensions:
                await self.load_extension(e)

    async def on_ready(self):
        print("Bot has connected to Discord!")
        await self.load_extensions(EXTENSIONS)

    async def add_cogs(self, cogs):
        print("Adding cogs.")
        for c in cogs:
            await self.add_cog(c)

    async def on_error(self, event, *args, **kwargs):
        logger.error(traceback.format_exc())

    async def send_message(self, channelID, message):
        channel = self.get_channel(channelID)
        await channel.send(message)


def getFilePath(filename):
    return os.path.join(DATA_PATH, filename)

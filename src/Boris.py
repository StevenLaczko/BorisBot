import json

import RunBoris
from src.helpers import DiscordBot
from src.cogs import Respondtron, MemeGrabber, ReminderCog

BOT_PREFIX = '~'

WEIGHTS = [1.2, 0.7, 1.1, 1]
PROB_MIN = 0.7
RESPONDTRON_NO_RESPONSE = "Use ~teach \"Trigger\" \"Response\" to teach me how to respond to something!"
RESPONDTRON_ARGS = {Respondtron.ARGS.WEIGHTS: WEIGHTS,
                    Respondtron.ARGS.PROB_MIN: PROB_MIN,
                    Respondtron.ARGS.DEBUG_CHANNEL_ID: 696863794743345152,
                    Respondtron.ARGS.ENABLE_AUTO_WEIGHTS: True,
                    Respondtron.ARGS.CONTEXT_LEN: 5}

# ReminderCog
REMINDER_FILE_NAME = "reminders.pkl"
MESSAGE_FLAG = "-m"

EXTENSIONS = [
    "src.BorisCommands"
]


# mafiaCog = MafiaCog.Mafia(bot, None, None)
# gptTest = GPT_Test.GPT_Test(bot)


class Boris(DiscordBot.DiscordBot):
    def __init__(self, bot_prefix=BOT_PREFIX, settings=None):
        super().__init__(bot_prefix, settings)

        self.event(self.on_member_join)

    # override parent class
    async def on_ready(self):
        await super().on_ready()
        await self.load_extensions(EXTENSIONS)
        await self.add_default_cogs()
        self.update_settings_file()

    async def add_default_cogs(self):
        await self.add_cogs([
            Respondtron.Respondtron(self, BOT_PREFIX, botNoResponse=RESPONDTRON_NO_RESPONSE),
            MemeGrabber.MemeGrabber(self),
            ReminderCog.ReminderCog(self, REMINDER_FILE_NAME, MESSAGE_FLAG)
        ])

    def update_settings_file(self):
        # update settings file on startup
        with open(RunBoris.SETTINGS_FILE, 'w') as f:
            json.dump(self.settings, f, indent=1)

    async def on_member_join(self, member):
        await self.send_message(658114649081774093, "<@!" + member.id + "> :gunworm:")



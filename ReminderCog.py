from discord.ext import commands, tasks
from discord import embeds
from pytz import timezone
from enum import Enum, auto
import dateutil.parser
from Message import Message
from Reminder import Reminder
from ReminderCogHelpers import *
from typing import List, Dict


class RemindType(Enum):
    MessageLink = auto  # links to a particular discord message
    String = auto  # sends the user the message they typed
    Message = auto


class RemindE(Enum):
    reminders = 0
    content = 1
    server = 2
    channel = 3
    dateTime = 4
    isActive = 5


REMINDER_FILE = "reminders"
DELAY_CHECK_REMINDERS_SEC = 5


class ReminderCog(commands.Cog):
    reminders = {}

    def __init__(self, bot):
        # load reminders from json file
        self.bot = bot
        try:
            self.reminders: Dict[int, List[Reminder]] = load_obj(REMINDER_FILE)
        except:
            self.GenerateReminderFile()

        self.lastSaved = datetime.datetime.now()
        self.LoopReminders.start()

    # sends the user a link to the command message at a given time
    @commands.command(name="remindMe", help="Usage: \"~remindMe N days\" or \"~remindMe M years\", etc")
    async def RemindMeCmd(self, ctx, *args):
        # frickin LOCAL ENUM
        num = 0
        dur = 1
        date = 0

        # handles wrong number of inputs
        if len(args) > 2:
            print("RemindMeCmd: Wrong num args. Number of args: ", len(args))
            await ctx.send("Command's wrong, bud. e.g. ~remindMe N hours/days/years")
            return

        # Handles if the user entered a particular date in the second argument instead of a time duration
        isDuration = False
        duration = None
        if len(args) == 2:
            duration = ParseDur(args[dur])
            if duration is not None:
                isDuration = True

        dateTime = None
        if not isDuration:
            est = timezone('US/Eastern')
            dateTime = dateutil.parser.parse(args[date])

        # Handles if the user entered a date
        if self.CheckUserKnown(ctx.message.author.id) is False:
            self.CreateUserKey(ctx.message.author.id)
        if dateTime is not None:
            self.AddReminder(ctx.message.author.id, ctx.channel.id, ctx.guild.id, dateTime, RemindType.MessageLink,
                             Message(ctx.message.content, ctx.message.jump_url))
            await ctx.message.add_reaction('✅')
            return

        # TODO: handle specific phrases to specify duration ("in a week", "in 2 months", etc.)
        # dateTime = self.parseDurPhrase()

        # Handles if the user entered a duration (N days/months/years)
        if args[num].isnumeric() and int(args[num]) > 0 and duration is not None:
            # CheckUserKnown checks if a user already has an entry in the database and gives them one if not
            if self.CheckUserKnown(ctx.message.author.id):
                # GetDateTime returns a date and time the user specifies
                dateTime = GetDateTimeFromDur(int(args[num]), duration)
                self.AddReminder(ctx.message.author.id, ctx.channel.id, ctx.guild.id, dateTime, RemindType.MessageLink,
                                 Message(ctx.message.content, ctx.message.jump_url))

    # Takes: user's id, a datetime object, a RemindType object, and some data (string, message link, etc)
    def AddReminder(self, userId, channelID, serverID, dateTime, remindType, data):
        print(f"Added Reminder: {dateTime} - {remindType}")
        self.reminders[userId].append(Reminder(data, remindType, channelID, serverID, dateTime))

        # todo handle different reminder types (not a message)

    # asynchronous loop that runs indefinitely every specified number of seconds
    @tasks.loop(seconds=5.0)
    async def LoopReminders(self):
        await self.bot.wait_until_ready()
        await self.CheckReminders()
        self.SaveReminderFile()

    @LoopReminders.before_loop
    async def Before_LoopReminders(self):
        print("Waiting for bot_ready to start loop...")
        await self.bot.wait_until_ready()

    # Loops through users in reminders. Returns true if user has a spot in the reminders dictionary
    def CheckUserKnown(self, userID):
        for storedUserId in self.reminders:
            if storedUserId == userID:
                return True
        return False

    # create user key in reminders dictionary
    def CreateUserKey(self, userID):
        self.reminders[userID] = []

    # iterate through all reminders and handle sending out reminders
    async def CheckReminders(self):
        dt = datetime.datetime
        now = dt.now()
        for u in self.reminders:
            if u != 0:
                for r_i in range(0, len(self.reminders[u])):
                    if now >= self.reminders[u][r_i].dateTime:
                        await self.RemindUser(u, r_i)

    # remind the user
    async def RemindUser(self, userID, rem_i, delete=True):
        await self.bot.wait_until_ready()
        reminder = self.reminders[userID][rem_i]
        dt = reminder.dateTime
        channel = self.bot.get_channel(reminder.channelID)
        message = "_ _"
        user = await self.bot.fetch_user(userID)
        eTitle = "Reminder for " + user.name
        eDesc = '\n'.join((dt.strftime("%x %X"), reminder.content.link, user.mention))
        # eUrl = reminder.content.link
        # eTimestamp = reminder.dateTime
        embed = None
        if reminder.type is RemindType.MessageLink:
            embed = embeds.Embed(title=eTitle, description=eDesc, )
        elif reminder.type is RemindType.Message:
            message = "Your reminder is here, friend!" + "\n" \
                      + "```" + reminder.content.link + "```" + "\n" \
                      + ">" + reminder.content.text
        await channel.send(embed=embed)

        if delete:
            del self.reminders[userID][rem_i]

    @commands.command(name="listRem")
    async def ListReminders(self, ctx):
        dt = datetime.datetime
        now = dt.now()
        for u in self.reminders:
            if u != 0:
                for r_i in range(0, len(self.reminders[u])):
                    user = await self.bot.fetch_user(u)
                    await ctx.send(
                        f"{user.name}: "
                        f"{self.reminders[u][r_i].dateTime} - {self.reminders[u][r_i].content.link}")

    # generate empty reminder json
    def GenerateReminderFile(self):
        # structure:
        # reminders = {
        #   userID [
        #         Reminder():
        #            content
        #            type
        #            channel
        #            dateTime
        #            isActive
        #   ]
        # }

        # dict of reminders
        self.reminders =  \
            {
                0: [],  # Sample (where u_id = 0):
            }

        self.SaveReminderFile()

    def SaveReminderFile(self):
        """with open(f"{os.getcwd()}/{REMINDER_FILE}", "w+") as reminderFile:
            json.dump(self.reminders, reminderFile, indent=6)
        localReminders = \
            {
                0: [],  # Sample (where u_id = 0):
            }

        for u in self.reminders:
            for r_i in range(0, len(self.reminders[u])):
                localReminders[u].append([self.reminders[u][r_i].content,
                                          self.reminders[u][r_i].type,
                                          self.reminders[u][r_i].channel,
                                          self.reminders[u][r_i].server,
                                          self.reminders[u][r_i].dateTime,
                                          self.reminders[u][r_i].isActive])"""

        save_obj(self.reminders, REMINDER_FILE)
        print("Saving reminder file...")


    """def LoadReminderFile(self, name):
        with open(REMINDER_FILE) as jsonReminders:
            self.reminders = json.load(jsonReminders)"""




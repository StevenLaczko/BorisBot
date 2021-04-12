import queue

from discord.ext import commands, tasks
from discord import embeds
from pytz import timezone
from enum import Enum, auto
import dateutil.parser
import traceback
from Message import Message
from PriorityQueuePeek import PriorityQueuePeek
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
REMINDER_Q_FILE = "reminders_q"
DELAY_CHECK_REMINDERS_SEC = 5


class ReminderCog(commands.Cog):
    reminders = {}

    def __init__(self, bot):
        # load reminders from json file
        self.bot = bot
        self.remindersQueue: PriorityQueuePeek = PriorityQueuePeek()
        self.LoadReminderFile(REMINDER_Q_FILE)

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

    # Loops through users in reminders. Returns true if user has a spot in the reminders dictionary
    def CheckUserKnown(self, userID):
        for storedUserId in self.reminders:
            if storedUserId == userID:
                return True
        return False

    # create user key in reminders dictionary
    def CreateUserKey(self, userID):
        self.reminders[userID] = []

    # Takes: user's id, a datetime object, a RemindType object, and some data (string, message link, etc)
    # BIG FAT OH OF FUUUUUUUUUUUUUUCKING logn
    def AddReminder(self, userId, channelID, serverID, dateTime, remindType, content):
        print(f"Added Reminder: {dateTime} - {remindType}")
        r = Reminder(content, userId, remindType, channelID, serverID, dateTime)
        self.InsertReminder(r)

        # todo handle different reminder types (not a message)

        self.SaveReminderFile()

    # asynchronous loop that runs indefinitely every specified number of seconds
    @tasks.loop(seconds=5.0)
    async def LoopReminders(self):
        await self.CheckNextReminder()

    @LoopReminders.before_loop
    async def Before_LoopReminders(self):
        print("Waiting for bot_ready to start loop...")
        await self.bot.wait_until_ready()

    # check nearest reminder (chronologically) to see if the time to remind has come
    # BIG OH OF FUUUUUUUUUUUUCKING ONE
    async def CheckNextReminder(self):
        r = self.PeekReminder()
        if r is None:
            return

        now = datetime.datetime.now()
        if now >= r.dateTime:
            await self.RemindUser()

    def PeekReminder(self):
        if len(self.remindersQueue.queue) > 0:
            return self.remindersQueue.peek()[1]

    def GetReminder(self) -> Reminder:
        if len(self.remindersQueue.queue) > 0:
            r = self.remindersQueue.get()[1]
            self.SaveReminderFile()
            return r

    # remind the user
    async def RemindUser(self, delete=True):
        if delete:
            reminder: Reminder = self.GetReminder()
        else:
            reminder: Reminder = self.PeekReminder()

        dt = reminder.dateTime
        channel = self.bot.get_channel(reminder.channelID)
        message = "_ _"
        user = await self.bot.fetch_user(reminder.userID)
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

        self.SaveReminderFile()

    @commands.command(name="listRem")
    async def ListReminders(self, ctx):
        dt = datetime.datetime
        now = dt.now()
        for r in self.remindersQueue.queue:
            user = await self.bot.fetch_user(r.userID)
            await ctx.send(
                f"{user.name}: "
                f"{r.dateTime} - {r.content.link}")

    @commands.command(name="convRem")
    async def ConvertReminders(self, ctx):
        try:
            oldReminders = load_obj(REMINDER_FILE)
            for u in oldReminders:
                for r in oldReminders[u]:
                    self.remindersQueue.put((r.dateTime, r))
            ctx.send("Yeet")
        except TypeError as e:
            if "tuple" in e.__str__():
                await ctx.send("The old reminder file ain't the right type. It's got tuples, friend.")
            else:
                await ctx.send("Some weird type error happened.")


    # generate empty reminder json
    def GenerateReminderFile(self):
        # structure:
        # in chronological order
        # reminders = [
        #      Reminder():
        #        content
        #        userID
        #        type
        #        channel
        #        dateTime
        #        isActive
        # ]

        self.remindersQueue = PriorityQueuePeek()

        self.SaveReminderFile()

    def InsertReminder(self, r: Reminder):
        self.remindersQueue.put((r.dateTime, r))

    def SaveReminderFile(self):
        save_obj(self.remindersQueue.queue, REMINDER_Q_FILE)
        print("Saving reminder file...")

    def LoadReminderFile(self, rFileName):
        try:
            q = load_obj(rFileName)
            self.remindersQueue.queue = q
            print("Loaded reminder file.")
        except (AttributeError, FileNotFoundError) as e:
            print("Didn't find reminder file. Generating.")
            self.GenerateReminderFile()

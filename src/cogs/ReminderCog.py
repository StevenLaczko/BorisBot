from discord.ext import commands, tasks
from discord import embeds
from enum import Enum
import dateutil.parser
import traceback
import os
from src.helpers import DiscordBot
from src.helpers.Message import Message
from src.helpers.PriorityQueuePeek import PriorityQueuePeek
from src.helpers.Reminder import Reminder
from src.helpers.ReminderCogHelpers import *


class RemindType(Enum):
    MessageLink = 0  # links to a particular discord message
    String = 1  # sends the user the message they typed


class RemindE(Enum):
    reminders = 0
    content = 1
    server = 2
    channel = 3
    dateTime = 4
    isActive = 5


MSG_FLAG = "-m"
DELAY_CHECK_REMINDERS_SEC = 5


class ReminderCog(commands.Cog):
    reminders = {}

    def __init__(self, bot, reminderFileName="reminders.pkl", msgFlag="-m"):
        # load reminders from json file
        self.bot = bot
        self.rFileName = reminderFileName
        self.msgFlag = msgFlag
        self.remindersQueue: PriorityQueuePeek = PriorityQueuePeek()
        self.LoadReminderFile(self.rFileName)

        self.lastSaved = datetime.datetime.now()
        self.LoopReminders.start()

    # sends the user a link to the command message at a given time
    @commands.command(name="remindMe",
                      help="~remindMe N hours/days/etc or ~remindMe (date) or ~remindMe (time)\n\
                      Use -m \"my message\" to add a message")
    async def RemindMeCmd(self, ctx, *args):
        # frickin LOCAL ENUM
        num = 0
        dur = 1
        date = 0
        # TODO: replace with actual enum
        # TODO TODO: actually parse the input smartly with regex or smthn
        # So... have a parse reminder function, loop through the args and find stuff wih regex and other funcs

        duration = None
        if len(args) > 1:
            duration = ParseDur(args[dur])

        if duration is not None:
            await self.RemindDur(ctx, args, duration)
            return
        else:
            await self.RemindDate(ctx, args)

    async def RemindDate(self, ctx, args):
        dateTime = dateutil.parser.parse(args[0])

        if dateTime is None:
            await ctx.message.add_reaction('❌')
            await ctx.send(f"Couldn't parse {args[0]}. B(")

        m, isMessage = GetMessage(self.msgFlag, args, ctx)
        remindType = RemindType.String if isMessage else RemindType.MessageLink
        newReminder = Reminder(Message(m, ctx.message.jump_url), ctx.message.author.id,
                               remindType, ctx.channel.id, ctx.channel.id, dateTime)
        try:
            await self.AddReminder(newReminder, ctx.message)
        except RuntimeError as e:
            print("ERROR: remindMe func failed to add a reminder")
            traceback.print_exc(e)
            await ctx.message.add_reaction('❌')
            await ctx.send('Something went wrong... Use ~help remindMe if you like.')

    async def RemindDur(self, ctx, args, duration):
        # check if message is correct format
        if not args[0].isnumeric() or not int(args[0]) > 0:
            return None

        # TODO: handle specific phrases to specify duration ("in a week", "in 2 months", etc.)
        # dateTime = self.parseDurPhrase()
        dateTime = GetDateTimeFromDur(int(args[0]), duration)

        m, isMessage = GetMessage(self.msgFlag, args, ctx)

        remindType = RemindType.String if isMessage else RemindType.MessageLink

        newReminder = Reminder(Message(m, ctx.message.jump_url), ctx.message.author.id,
                               remindType, ctx.channel.id, ctx.channel.id, dateTime)
        try:
            await self.AddReminder(newReminder, ctx.message)
        except RuntimeError as e:
            print("ERROR: remindMe func failed to add a reminder")
            traceback.print_exc(e)
            await ctx.message.add_reaction('❌')
            await ctx.send('Something went wrong... Use ~help remindMe if you like.')

    # Takes: user's id, a datetime object, a RemindType object, and some data (string, message link, etc)
    # BIG FAT OH OF FFFFFFFFF logn
    async def AddReminder(self, r: Reminder, msg):
        print(f"Added Reminder: {r.dateTime} - {r.remindType}")
        self.InsertReminder(r)
        # todo handle different reminder types (not a messagelink)

        self.SaveReminderFile()

        if msg is not None:
            await msg.add_reaction('✅')

    # asynchronous loop that runs indefinitely every specified number of seconds
    @tasks.loop(seconds=5.0)
    async def LoopReminders(self):
        await self.CheckNextReminder()

    # check nearest reminder (chronologically) to see if the time to remind has come
    # BIG OH OF FROCKING ONE
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
        message = reminder.content.text
        remindType = reminder.remindType
        user = await self.bot.fetch_user(reminder.userID)
        title = f"Your reminder is here, {user.name}!"
        link = reminder.content.link

        desc = []
        if remindType == RemindType.String:
            desc.append("<< " + message + " >>")
        desc.append(reminder.content.link)
        desc.append(user.mention)
        desc = '\n'.join(desc)

        embed = None
        embed = embeds.Embed(title=title, description=desc)
        embed.set_footer(text=dt.strftime("%x %X"))
        await channel.send(embed=embed)

        self.SaveReminderFile()

    @commands.command(name="listRem")
    @commands.is_owner()
    async def ListReminders(self, ctx):
        dt = datetime.datetime
        now = dt.now()
        for r in self.remindersQueue.queue:
            user = await self.bot.fetch_user(r.userID)
            await ctx.send(
                f"{user.name}: "
                f"{r.dateTime} - {r.content.link}")

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

    # TODO TODO TODO please god save these reminders as json, not PKL
    def SaveReminderFile(self):
        defReminderFilePath = DiscordBot.getFilePath("reminders_q.pkl")
        reminderFilePath = DiscordBot.getFilePath(self.rFileName)
        if os.path.exists(defReminderFilePath):
            os.rename(defReminderFilePath, reminderFilePath)

        save_obj(self.remindersQueue.queue, self.rFileName)
        print("Saving reminder file...")

    def LoadReminderFile(self, rFileName):
        try:
            q = load_obj(rFileName)
            self.remindersQueue.queue = q
            print("Loaded reminder file.")
        except (AttributeError, FileNotFoundError) as e:
            print("Didn't find reminder file. Generating.")
            self.GenerateReminderFile()

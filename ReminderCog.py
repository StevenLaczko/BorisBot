import pickle
import time

from discord.ext import commands, tasks
from discord import embeds
from pytz import timezone
from enum import Enum, auto
import datetime
import asyncio
import dateutil.parser
import re
import StringMatchHelp

REMINDER_FILE = "reminders.json"
DELAY_CHECK_REMINDERS_SEC = 5


class DURATIONS(Enum):
    years = 0
    month = 1
    days = 2
    hours = 3
    minutes = 4
    seconds = 5
    microseconds = 6
    centuries = 7
    millenia = 8


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


class Message:
    def __init__(self, text, link):
        self.text = text
        self.link = link


class Reminder():
    def __init__(self, content, type, channel, server, dateTime, isActive=True):
        self.content = content
        self.type = type
        self.channel = channel
        self.server = server
        self.dateTime = dateTime
        self.isActive = isActive

#TODO
# save and load reminders (should be easy)

class ReminderCog(commands.Cog):
    reminders = {}

    def __init__(self, bot):
        # load reminders from json file
        self.bot = bot
        try:
            self.reminders = load_obj(REMINDER_FILE)
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
        try:
            est = timezone('US/Eastern')
            dateTime = dateutil.parser.parse(args[date])
        except:
            dateTime = None

        # Handles if the user entered a date
        if self.CheckUserKnown(ctx.message.author.id) is False:
            self.CreateUserKey(ctx.message.author.id)
        if dateTime is not None:
            self.AddReminder(ctx.message.author.id, ctx.channel, ctx.guild, dateTime, RemindType.MessageLink,
                             Message(ctx.message.content, ctx.message.jump_url))
            await ctx.message.add_reaction('✅')
            return

        # TODO: handle specific phrases to specify duration ("in a week", "in 2 months", etc.)
        # dateTime = self.parseDurPhrase()

        # Handles if the user entered a duration (N days/months/years)
        try:
            duration = self.ParseDur(args[dur])
            if args[num].isnumeric() and args[num] > 0 and duration is not None:
                # CheckUserKnown checks if a user already has an entry in the database and gives them one if not
                if self.CheckUserKnown(ctx.message.author.id):
                    # GetDateTime returns a date and time the user specifies
                    dateTime = GetDateTimeFromDur(args[num], duration)
                    self.AddReminder(ctx.message.author.id, ctx.channel, ctx.guild, dateTime, RemindType.MessageLink,
                                     Message(ctx.message.content, ctx.message.jump_url))
        except:
            print("Was not a duration")

    # Takes: user's id, a datetime object, a RemindType object, and some data (string, message link, etc)
    def AddReminder(self, userId, channel, server, dateTime, remindType, data):
        self.reminders[userId].append(Reminder(data, remindType, channel, server, dateTime))

        # todo handle different reminder types (not a message)

    # inputs duration string (days, months, years, etc), outputs
    def ParseDur(self, durStr):
        for dur in DURATIONS:
            if StringMatchHelp.fuzzyMatchString(durStr, dur.__name__, StringMatchHelp.DEF_WEIGHTS,
                                                StringMatchHelp.DEF_PROB) \
                    [StringMatchHelp.Output.isMatch] is True:
                return dur
        return None

    # Loops through users in reminders. Returns true if user has a spot in the reminders dictionary
    def CheckUserKnown(self, userID):
        for storedUserId in self.reminders:
            if storedUserId == userID:
                return True
        return False

    # create user key in reminders dictionary
    def CreateUserKey(self, userID):
        self.reminders[userID] = []

    # asynchronous loop that runs indefinitely every specified number of seconds
    @tasks.loop(seconds=5.0)
    async def LoopReminders(self):
        await self.CheckReminders()

    @LoopReminders.before_loop
    async def Before_LoopReminders(self):
        print("Waiting for bot_ready to start loop...")
        await self.bot.wait_until_ready()

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
    async def RemindUser(self, userID, rem_i):
        reminder = self.reminders[userID][rem_i]
        channel = self.bot.get_channel(reminder.channel.id)
        message = "_ _"
        eTitle = "Reminder for " + self.bot.get_user(userID).name
        eDesc = reminder.content.link + "\n" + self.bot.get_user(userID).mention
        #eUrl = reminder.content.link
        #eTimestamp = reminder.dateTime
        embed = None
        if reminder.type is RemindType.MessageLink:
            embed = embeds.Embed(title=eTitle, description=eDesc)
        elif reminder.type is RemindType.Message:
            message = "Your reminder is here, friend!" + "\n" \
                      + "```" + reminder.content.link + "```" + "\n" \
                      + ">" + reminder.content.text
        await channel.send(embed=embed)
        del self.reminders[userID][rem_i]

    # generate empty reminder json
    def GenerateReminderFile(self):
        # structure:
        # reminders {
        #   userID {
        #       content
        #       type
        #       channel
        #       dateTime
        #       isActive
        #   }
        # }

        self.reminders = \
            {
                0:
                    []
            }


# takes a number num of a time duration dur, gets the date that far into the future
def GetDateTimeFromDur(num, dur):
    dt = datetime.datetime
    now = dt.now()

    # get args to create a datetime object to represent the user's specified time delta
    dtNumArgs = 7
    args = [0] * dtNumArgs
    args[dur] = num

    # get and return the time after the user's specified time delta from now
    timeDelta = datetime.datetime(args[0], args[1], args[2], args[3], args[4], args[5], args[6])
    remindTime = now + timeDelta
    return remindTime

# FIXME use these to put notes into CSV
def ConvertNoteToEscapedForm(str):
    return str.replace('\n', '\\n')

def ConvertEscapedFormToNote(str):
    return str.replace('\\n', '\n')

def save_obj(obj, name):
    with open('obj/' + name + '.pkl', 'wb+') as f:
        pickle.dump(obj, f, pickle.DEFAULT_PROTOCOL)


def load_obj(name):
    with open('obj/' + name + '.pkl', 'rb') as f:
        return pickle.load(f)

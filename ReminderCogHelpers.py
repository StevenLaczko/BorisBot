import re
from enum import IntEnum
import datetime
import pickle

import dateutil.parser

import StringMatchHelp
from ReminderCog import TIME_REGEX, DATE_REGEX


class DURATIONS(IntEnum):
    milliseconds = 0,
    microseconds = 1,
    seconds = 2,
    minutes = 3,
    hours = 4,
    days = 5,
    weeks = 6,
    months = 7,
    years = 8,
    centuries = 9


# takes a number num of a time duration dur, gets the date that far into the future
def GetDateTimeFromDur(num, dur):
    dt = datetime.datetime
    now = dt.now()

    # get args to create a datetime object to represent the user's specified time delta
    # args = [years, months, days, hours, minutes, seconds, microseconds]
    dtNumArgs = 10
    args = [0] * dtNumArgs  # creates list with dtNumArgs number of items
    args[dur] = num
    args[DURATIONS.days] += 365 * args[DURATIONS.years]
    args[DURATIONS.weeks] += 4 * args[DURATIONS.months]
    args[DURATIONS.weeks] += 100 * 52 * args[DURATIONS.centuries]

    # get and return the time after the user's specified time delta from now
    remindTime = now + datetime.timedelta(milliseconds=args[DURATIONS.milliseconds],
                                          microseconds=args[DURATIONS.microseconds],
                                          seconds=args[DURATIONS.seconds],
                                          minutes=args[DURATIONS.minutes],
                                          hours=args[DURATIONS.hours],
                                          days=args[DURATIONS.days],
                                          weeks=args[DURATIONS.weeks])

    return remindTime


def IfTimeGet(messageTuple):
    message = " ".join(messageTuple)
    time = re.match(TIME_REGEX, message)
    date = re.match(DATE_REGEX, message)
    timestamp = f"{time} {date}"
    dateTime = dateutil.parser.parse(timestamp)
    return dateTime


def IfDurationGet(messageTuple):
    message = " ".join(messageTuple)
    return ParseDur(message)


# inputs duration string (days, months, years, etc), outputs
def ParseDur(message: str):
    for dur in DURATIONS:
        if dur.__name__ in message:
            return dur
    return None


def GetMessage(msgFlag, args, ctx=None):
    for i in range(len(args)):
        if args[i] == msgFlag:
            return args[i + 1], True

    return ctx.message.content, False


# FIXME use these to put notes into CSV
def ConvertNoteToEscapedForm(str):
    return str.replace('\n', '\\n')


def ConvertEscapedFormToNote(str):
    return str.replace('\\n', '\n')


def save_obj(obj, name):
    name = ensure_pkl_ext(name)
    with open('obj/' + name, 'wb+') as f:
        pickle.dump(obj, f, pickle.DEFAULT_PROTOCOL)


def load_obj(name):
    name = ensure_pkl_ext(name)
    with open('obj/' + name, 'rb') as f:
        return pickle.load(f)


def ensure_pkl_ext(name):
    ext = ".pkl"
    if name[-4:] == ext:
        ext = ""
    return name + ext

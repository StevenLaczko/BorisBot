import unittest
import os
import datetime
from discord.ext import commands

from ReminderCog import ReminderCog
from ReminderCog import REMINDER_FILE
from ReminderCog import RemindType

class MyTestCase(unittest.TestCase):
    def setUp(self) -> None:
        try:
            os.rename(REMINDER_FILE, f"save_{REMINDER_FILE}")
        except FileNotFoundError:
            print(f"{REMINDER_FILE} file doesn't exist.")

        self.bot = commands.Bot(command_prefix="")
        self.rc = ReminderCog(self.bot)

    def tearDown(self) -> None:
        try:
            os.rename(f"save_{REMINDER_FILE}", REMINDER_FILE)
        except FileNotFoundError:
            print(f"save_{REMINDER_FILE} file doesn't exist.")

    def test_reminder_queue_insertion(self):
        self.rc.GenerateReminderFile()
        now = datetime.datetime.now()
        self.rc.AddReminder(2, 2, 2, now + datetime.timedelta(minutes=2), remindType=RemindType.MessageLink, data="")
        self.rc.AddReminder(1, 1, 1, now + datetime.timedelta(minutes=1), remindType=RemindType.MessageLink, data="")
        self.rc.AddReminder(3, 3, 3, now + datetime.timedelta(minutes=3), remindType=RemindType.MessageLink, data="")
        self.assertEqual(1, self.rc.GetReminder().userID)
        self.assertEqual(2, self.rc.GetReminder().userID)
        self.assertEqual(3, self.rc.GetReminder().userID)

    def test_reminders_save_load(self):
        pass



if __name__ == '__main__':
    unittest.main()

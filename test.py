import unittest
import os
import datetime
from discord.ext import commands

from ReminderCog import ReminderCog
from ReminderCog import REMINDER_Q_FILE
from ReminderCog import RemindType


class MyTestCase(unittest.TestCase):
    def setUp(self) -> None:
        try:
            os.rename(f"{REMINDER_Q_FILE}.pkl", f"save_{REMINDER_Q_FILE}.pkl")
        except FileNotFoundError:
            print(f"{REMINDER_Q_FILE} file doesn't exist.")

        self.bot = commands.Bot(command_prefix="")
        self.rc = ReminderCog(self.bot)
        self.now = datetime.datetime.now()

    def tearDown(self) -> None:
        try:
            os.rename(f"save_{REMINDER_Q_FILE}", REMINDER_Q_FILE)
        except FileNotFoundError:
            print(f"save_{REMINDER_Q_FILE} file doesn't exist.")

    def test_reminder_queue_insertion(self):
        self.rc.GenerateReminderFile()
        self.add_reminders()
        self.assert_reminders()
        self.assertIsNone(self.rc.GetReminder())

    def test_reminders_save_load(self):
        self.reset_rc()
        self.rc.GenerateReminderFile()
        self.add_reminders()
        self.assert_reminders()
        self.rc.SaveReminderFile()
        self.reset_rc()
        self.rc.LoadReminderFile(REMINDER_Q_FILE)

    def reset_rc(self):
        self.rc = None
        self.rc = ReminderCog(self.bot)

    def add_reminders(self):
        self.rc.AddReminder(2, 2, 2, self.now + datetime.timedelta(minutes=2), remindType=RemindType.MessageLink,
                            content="")
        self.rc.AddReminder(1, 1, 1, self.now + datetime.timedelta(minutes=1), remindType=RemindType.MessageLink,
                            content="")
        self.rc.AddReminder(3, 3, 3, self.now + datetime.timedelta(minutes=3), remindType=RemindType.MessageLink,
                            content="")

    def assert_reminders(self):
        self.assertEqual(1, self.rc.GetReminder().userID)
        self.assertEqual(2, self.rc.GetReminder().userID)
        self.assertEqual(3, self.rc.GetReminder().userID)
        self.assertIsNone(self.rc.GetReminder())


if __name__ == '__main__':
    unittest.main()

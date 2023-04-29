import json
import unittest

from src.cogs.NLPResponder.Context import Context
from src.cogs.NLPResponder.Memory.MemoryPool import MemoryPool
from src.cogs.NLPResponder.commands import BorisCommands

context_dict = """{
  "MEMORY_IDS": [],
  "TRIGGERS": [
    {
      "TYPE": "USERS-INCLUDED",
      "USER_IDS": []
    },
    {
      "TYPE": "USERS-EXCLUDED",
      "USER_IDS": []
    },
    {
      "TYPE": "CHAT_TYPE",
      "CHAT_TYPE": "DM"
    },
    {
      "TYPE": "TOPIC",
      "TOPIC": "Boris"
    }
  ],
  "PROMPTS": {
    "CHARACTER": {
      "CONTENT": "",
      "MODE": "REPLACE"
    },
    "PURPOSE": {
      "CONTENT": "",
      "MODE": "REPLACE"
    },
    "MEMORY": {
      "CONTENT": "These are your memories.....",
      "MODE": "REPLACE"
    },
    "COMMANDS_PREPEND": {
      "CONTENT": "",
      "MODE": "REPLACE"
    },
    "COMMANDS": {
      "NAMES": [
          "RESPOND",
          "MOOD",
          "REMEMBER"
      ],
      "MODE": "REPLACE",
      "PREFIX": "!"
    },
    "FINAL": {
      "CONTENT": "",
      "MODE": "REPLACE"
    }
  }
}"""

class BrainTests(unittest.TestCase):
    def test_context_creation(self):
        mem_pool = MemoryPool()
        d: dict = json.loads(context_dict)
        c = Context(mem_pool, d, command_funcs=BorisCommands.commands)
        f_names = [f.__name__ for f in c.commands.values()]
        for n in d["PROMPTS"]["COMMANDS"]["NAMES"]:
            assert n + 'Command' in f_names

        assert "CHARACTER" in c.prompts.keys()

    def test_context_stack_methods(self):
        pass

    #def test_bot_reply(self):
    #    context_dir = "data/contexts/"
    #    c_files = ["main-context.json"]
    #    SETTINGS_FILE = "data/settings.json"
    #    bot = Boris(settings_path=SETTINGS_FILE)
    #    bot_brain = BotBrain(bot, context_dir=context_dir, context_files=c_files, commands=BorisCommands.commands)



if __name__ == '__main__':
    unittest.main()

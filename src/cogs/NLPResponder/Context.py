import json

from ordered_set import OrderedSet

MAX_MEMORIES = 8

class Context:
    def __init__(self, memory_pool, name=None, json_filepath=None, context_dict=None, command_funcs=None, prompts=None, memory=None, triggers=None, mood=None):
        self.name = name
        self.json_filepath = json_filepath
        self.memory_pool = memory_pool
        self.prompts = prompts
        self._memory: OrderedSet = OrderedSet(memory) if memory else OrderedSet()
        self._triggers = triggers
        self.commands: dict = None
        self.mood = mood
        if context_dict:
            self.init_context(context_dict, command_funcs)

    def init_context(self, d, funcs):
        self.name = d["NAME"]

        for m_id in d["MEMORY_IDS"]:
            self._memory.add(m_id)

        if not self._triggers:
            self._triggers = []
        for tr in d["TRIGGERS"]:
            self._triggers.append(tr)

        if not funcs:
            raise ValueError("No command functions passed into bot.")
        if not self.prompts:
            self.prompts = d["PROMPTS"]

        self.commands = {}
        for c in d["PROMPTS"]["COMMANDS"]["CONTENT"]:
            c_name = c["NAME"]
            for f in funcs:
                dict_name = c_name + "Command"
                if dict_name == f.__class__.__name__:
                    self.commands[dict_name] = f
                    break

        self._memory.update(d["MEMORY_IDS"])

    def get_memory_ids(self):
        return self._memory

    def save_to_contextfile(self):
        with open(self.json_filepath, 'r') as f:
            obj = json.load(f)
        obj["MEMORY_IDS"] = list(self._memory)
        with open(self.json_filepath, 'w') as f:
            json.dump(obj, f, indent=4)


    def add_memory(self, mem_id):
        self._memory.add(mem_id)
        # TODO replace this with giving memories scores based on usefulness (similarity to boris response)
        if len(self._memory) > MAX_MEMORIES:
            self._memory.pop(len(self._memory)-1)
        self.save_to_contextfile()

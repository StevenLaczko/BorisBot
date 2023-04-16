from ordered_set import OrderedSet


class Context:
    def __init__(self, memory_pool, name=None, context_dict=None, command_funcs=None, prompts=None, memory=None, triggers=None, mood=None):
        self.name = name
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

    def get_memory_ids(self):
        return self._memory

    def add_memory(self, mem_id):
        self._memory.add(mem_id)


class Context:
    def __init__(self, prompts = None, memory = None, triggers = None):
        self._prompts = prompts
        self._memory = memory
        self._triggers = triggers

    def get_memories(self):
        pass

    def add_memory(self, new_memory):
        pass
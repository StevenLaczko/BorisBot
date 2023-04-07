from ordered_set import OrderedSet


class Context:
    def __init__(self, memory_pool, prompts=None, memory=None, triggers=None, mood=None):
        self.memory_pool = memory_pool
        self._prompts = prompts
        self._memory: OrderedSet = OrderedSet(memory) if memory else OrderedSet()
        self._triggers = triggers
        self.mood = mood

    def get_memory_ids(self):
        return self._memory

    def add_memory(self, mem_id):
        self._memory.add(mem_id)

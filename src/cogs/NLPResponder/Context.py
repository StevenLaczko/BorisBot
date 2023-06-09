import json

from ordered_set import OrderedSet

from src.cogs.NLPResponder.Memory.Memory import Memory
from src.helpers.logging_config import logger

MAX_MEMORIES = 5


class Context:
    def __init__(self, memory_manager, name=None, json_filepath=None, context_dict=None, command_funcs=None, prompts=None,
                 memory=None, triggers=None):
        self.name = name
        self.json_filepath = json_filepath
        self.memory_manager = memory_manager
        self.prompts = prompts
        self._memory: OrderedSet = OrderedSet(memory) if memory else OrderedSet()
        self._triggers = triggers
        self.commands: dict = None
        self.temperature = None
        if context_dict:
            self.init_context(context_dict, command_funcs)

    def init_context(self, d, funcs):
        self.name = d["NAME"]

        if "TEMPERATURE" in d and not self.temperature:
            self.temperature = d["TEMPERATURE"]

        ids = [x for x in d["MEMORY_IDS"]]
        for mem_id in ids:
            if self.memory_manager.get_memory_from_id(mem_id) is None:
                d["MEMORY_IDS"].remove(mem_id)
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

    def save_to_contextfile(self):
        with open(self.json_filepath, 'r') as f:
            obj = json.load(f)
        obj["MEMORY_IDS"] = list(self._memory)
        with open(self.json_filepath, 'w') as f:
            json.dump(obj, f, indent=4)

    def prune_memories(self, num_remove, max_memories=MAX_MEMORIES):
        if len(self._memory) <= max_memories:
            logger.debug(f"Context '{self.name}': {len(self._memory)}, max: {max_memories}")
            return
        m_list: list[Memory] = self.memory_manager.get_memories_from_ids(self._memory)
        m_list_sorted: list[Memory] = sorted(m_list, key=lambda x: x.score)
        removed_mem_str = '\n'.join([str(x) for x in m_list_sorted[:num_remove]])
        logger.info(f"Context '{self.name}': Pruning {num_remove} memories:\n{removed_mem_str}")
        for m in m_list_sorted[:num_remove]:
            self._memory.remove(m.id)

    def add_memory(self, mem):
        self._memory.add(mem.id)
        self.prune_memories(3)
        self.save_to_contextfile()

import uuid

from ordered_set import OrderedSet
from src.helpers.logging_config import logger


class ContextStack(OrderedSet):
    def __init__(self, context_dict, memory_pool, context=None, contexts=None, use_main_context=True):
        super().__init__()
        self.memory_pool = memory_pool
        self.context_dict = context_dict

        if use_main_context:
            self.use_main()
        if context and contexts:
            logger.error(
                "ERROR both context and context list passed into ContextStack constructor. Pick one or the other.")
        elif context:
            self.add(context)
        elif contexts:
            for c in contexts:
                self.add(c)

    def use_main(self):
        return self.add(self.context_dict["main"])

    def get_memory_ids(self) -> list[uuid.UUID]:
        ids: list[uuid.UUID] = []
        for context in self:
            ids.extend(context.get_memory_ids())
        return ids

    def save_memory(self, mem_id):
        for context in self:
            context.add_memory(mem_id)

    def add_memory(self, new_memory):
        pass

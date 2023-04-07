from src.helpers.logging_config import logger
from src.cogs.NLPResponder.Context import Context

class ContextStack:
    def __init__(self, context=None, contexts=None, use_main_context=True):
        if use_main_context:
            self.contexts = self.default_context_stack()
        if context and contexts:
            logger.error("ERROR both context and context list passed into ContextStack constructor. Pick one or the other.")
        elif context:
            self.contexts = [context]
        elif contexts:
            self.contexts = contexts


    def default_context_stack(self):
        return Context(prompts=DEFAULT_PROMPTS, memory=MAIN_MEMORY, triggers=DEFAULT_TRIGGERS)

    def get_memories(self):
        pass

    def add_memory(self, new_memory):
        pass

import uuid

from ordered_set import OrderedSet

from src.cogs.NLPResponder.Context import Context
from src.cogs.NLPResponder.Prompt import Prompt
from src.helpers.logging_config import logger


class ContextStack(OrderedSet):
    def __init__(self, context_dict, memory_manager, context=None, contexts=None, use_main_context=True):
        super().__init__()
        self.context_dict: dict = context_dict

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

    async def execute_commands(self, bot_brain, message, conversation, commands: dict[str, list]) -> dict[str, object]:
        funcs = self.get_command_funcs()
        returns: dict[str, object] = {}
        for c_name in commands.keys():
            name = c_name + "Command"
            if name in funcs:
                logger.info(f"Executing {name} with args {commands[c_name]}")
            r = await funcs[name].execute(bot_brain, message, conversation, commands[c_name][:-1], **commands[c_name][-1])
            if r:
                returns[c_name] = r
        return returns

    def get_command_funcs(self) -> dict[str, any]:
        command_dict = {}
        for c in self:
            command_dict.update(c.commands)
        return command_dict

    def get_combined_prompt(self, message, conversation):
        prompt: Prompt = Prompt()
        for c in self:
            prompt.stack(c)
        return prompt

    def get_memory_ids(self) -> list[int]:
        ids: list[int] = []
        for context in self:
            ids.extend(context.get_memory_ids())
        return ids

    def save_memories_to_contextfiles(self):
        for context in self:
            context.save_to_contextfile()

    def add_memory_to_contexts(self, memory):
        for context in self:
            context.add_memory(memory)


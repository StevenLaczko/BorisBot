from typing import Union

from src.helpers.logging_config import logger

from src.cogs.NLPResponder.Context import Context


class Prompt:
    def __init__(self, prompt_dict: dict = None):
        self.prompt_dict = prompt_dict

    def stack(self, context: Context):
        if not self.prompt_dict:
            self.prompt_dict = context.prompts
            return
        p = context.prompts
        for k in self.prompt_dict:
            replace = False
            if k in p and "MODE" in p[k]:
                if p[k]["MODE"] == "REPLACE":
                    replace = True

            new_content = p[k]["CONTENT"]
            if replace:
                self.prompt_dict[k]["CONTENT"] = new_content
            else:
                if k == "COMMANDS":
                    self.prompt_dict[k]["CONTENT"].extend(new_content)
                else:
                    self.prompt_dict[k]["CONTENT"] += '\n' + new_content

    def get_prompt(self, dynamic_prompts: Union[dict, None] = None) -> str:
        result = []
        for k, v in self.prompt_dict.items():
            content = None
            if "CONTENT" in v:
                content = v["CONTENT"]
            if k == "COMMANDS" and content:
                prefix = v["PREFIX"]
                for command in content:
                    usage = prefix + command["USAGE"]
                    desc: str = command["DESCRIPTION"]
                    command_str = usage + '\n' + desc + '\n' if len(desc.strip()) != 0 else usage + '\n'
                    result.append(command_str)
            elif len(v.keys()) == 0 and dynamic_prompts:
                if dynamic_prompts[k]:
                    result.append(dynamic_prompts[k])
            else:
                result.append(content)
        r = '\n'.join(result)
        return r

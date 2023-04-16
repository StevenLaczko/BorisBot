import abc
import json

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

    def get_prompt(self) -> str:
        result = []
        for k, v in self.prompt_dict.items():
            content = v["CONTENT"]
            if k != "COMMANDS":
                result.append(content)
            else:
                prefix = v["PREFIX"]
                for command in content:
                    usage = prefix + command["USAGE"]
                    desc = command["DESCRIPTION"]
                    result.append(usage + '\n' + desc)
        return '\n'.join(result)

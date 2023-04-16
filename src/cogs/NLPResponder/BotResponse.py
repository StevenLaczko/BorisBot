from typing import Union
from src.helpers.Settings import settings

class BotResponse:
    def __init__(self, full_response):
        self.full_response: str = full_response
        self.commands = self.parseBotCommands(full_response)

    def parseBotCommands(self, full_response_str) -> list[tuple]:
        response_split: list[str] = full_response_str.split('\n')
        commands: list[tuple] = []
        cur_cmd_str = ""
        cur_cmd_name = ""
        i = 0
        while i < len(response_split):
            cmd_start = response_split[i].startswith(settings.prefix)
            cur_line = response_split[i]
            if cmd_start:
                # append previous command to commands list
                if len(cur_cmd_str) != 0:
                    commands.append((cur_cmd_name, cur_cmd_str))
                    cur_cmd_str = ""
                    cur_cmd_str = ""
                # take off !<command> part and add line to cmd_str
                space_index = cur_line.find(' ')
                if space_index == -1:
                    space_index = len(cur_line)
                cur_cmd_name = cur_line[1:space_index]
                if space_index < len(cur_line)-1:
                    cur_cmd_str += cur_line[space_index+1:]
            else:
                cur_cmd_str += '\n' + cur_line

            if i == len(response_split)-1:
                commands.append((cur_cmd_name, cur_cmd_str))

            i += 1

        return commands


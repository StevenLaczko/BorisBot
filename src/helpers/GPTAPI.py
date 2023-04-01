import enum
from typing import Union

import discord
from dotenv import load_dotenv
import logging
import os
import openai
from src.helpers import DiscordBot
import json

logging.basicConfig(level=logging.INFO)


class Role(enum.Enum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


SYSTEM_MESSAGE = None
CHARACTER_PROMPT = [
    f"Alright partner, from now on, yer gonna respond as a digital friend named Boris. Boris acts and speaks like the Engi from TF2, but he was made by a fella named Steven."
]
DIALECT_EXAMPLES = [
    {"role": "user", "content": "List some examples of the Engineer from TF2 as a dialect example."},
    {"role": "assistant",
     "content": """ "Well, I'll be a hornswogglin' son of a gun, looks like we got ourselves a situation here."
"Mmm-hmm, we're gonna need more metal to build this here contraption."
"Y'all better git ready, 'cause we're fixin' to give 'em a good ol' fashioned Texas-style beatdown."
"I tell you what, this gizmo here is more complicated than a cat tryin' to bury a turd on a marble floor." """
     }
]
RESPONSE_EXAMPLE = [
    """```Chatlog
    Steven: yeah that is ridiculous
    Kristian: What is :pensive:?
    ```
    ```Response
    What's so doggon crazy about it, boys?
    ``` """
]
FORMAT_COMMANDS = [
    "I'm gonna give ya a chat log and you're gonna respond with a single message as Boris. You will write no explanation or anything else, ya hear? Always speak in a southern dialect like the Engi, with colloquialisms.",
    "Never type out \"Boris:\" at the start of your messages. Never send an empty message."
]

COMMAND_INSTRUCTIONS = """You have access to a Remember and a Mood command. You can use one, both, or neither of the commands. When you want to remember something or set your own Mood, use this format:
```example
Mood: [single word to describe mood]
Remember: [text to remember]
[boris' response to the chatlog]
```"""

CONFIRM_UNDERSTANDING = [
    {"role": "user", "content": "If you understand, respond with a single '.' this time, but never again."},
    {"role": "assistant", "content": "."}
]

MEMORY_PREPROMPT = "I am going to give you a list of statements. Lower the word count. Keep all details, no matter how small. Just rewrite to lower the word count. Explain nothing and respond only with the shorter list of statements separated by newlines. Keep each memory separate. Always keep names."

MOOD_PREPROMPT = "I am going to give you a list of statements. You are the AI friend Boris in the log. Determine what mood Boris should have after having the following conversation and give a reason."

MOOD_FORMAT_COMMANDS = "Write your response in this format:\n```format\nReason: [explain reason for mood]\n[mood]\n```\nWrite the reason on a single line, and write the mood as a single word. Do not use any markdown."

TEMPERATURE = 0.75
FREQ_PENALTY = 1
REMEMBER_TEMPERATURE = 0
REMEMBER_FREQ_PENALTY = 0
MEMORY_WORD_COUNT_MAX = 300
with open(DiscordBot.getFilePath("settings.json")) as f:
    id_name_dict = json.loads(f.read())["id_name_dict"]


def promptGPT(gptMessages, temperature=TEMPERATURE, frequency_penalty=FREQ_PENALTY):
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=gptMessages,
        temperature=REMEMBER_TEMPERATURE,
        presence_penalty=REMEMBER_FREQ_PENALTY,
        frequency_penalty=REMEMBER_FREQ_PENALTY
    )

    return {"string": response["choices"][0]["message"]["content"].strip(), "object": response}


def getMessageStr(bot, message, writeBotName=False):
    if writeBotName or bot.user.id != message.author.id:
        name = id_name_dict[message.author.id] if message.author.id in id_name_dict else None
        nick_str = message.author.name
        name_str = f"{name} (AKA {nick_str})" if name else nick_str
        result = f"{name_str}: {message.clean_content}"
    else:
        result = message.clean_content

    return result


def createGPTMessage(_input: Union[str, list, dict], role: Role = None) -> list[dict[str, str]]:
    result = []
    if role is None:
        logging.warning("Assuming 'user' role for GPT message creation.")
        role = Role.USER
    role = role.value
    if isinstance(_input, str):
        if len(_input) != 0:
            result = [{"role": role, "content": _input}]
    elif isinstance(_input, list):
        if isinstance(_input[0], str):
            for s in _input:
                result.append({"role": role, "content": s})
        elif isinstance(_input[0], dict):
            result = _input
    elif isinstance(_input, dict):
        result = [_input]

    return result


def getContextGPTPlainMessages(bot, messages: list[discord.Message]):
    result_str = ""

    for m in messages:
        result_str += getMessageStr(bot, m, writeBotName=True) + '\n'

    return result_str


def getContextGPTChatlog(bot, messages: list[discord.Message]):
    result: list[dict] = []
    log_str = ""

    def appendLogStr(_log_str=log_str):
        result.extend(createGPTMessage(_log_str, Role.USER))

    def appendBotStr(_m):
        result.extend(createGPTMessage(_m.clean_content, Role.ASSISTANT))

    for m in messages:
        if m.author.id == bot.user.id:
            if log_str != "":
                appendLogStr(log_str)
                log_str = ""
            appendBotStr(m)

        else:
            log_str += getMessageStr(bot, m) + '\n'

    if log_str != "":
        appendLogStr(log_str)

    return result


def getMemoryString(memory: list[str]) -> str:
    if len(memory) != 0:
        memory_str = f"Here are your preexisting memories as Boris:\n```"
        for m in memory:
            if not m:
                continue
            memory_str += '\n' + m
        memory_str += '```'
    else:
        memory_str = ""

    return memory_str


def buildGPTMessageLog(*args):
    result = []
    for a in args:
        result.extend(createGPTMessage(a))
    return result


def getMoodString(mood: (str, str)):
    if len(mood) != 0:
        result = f"Boris' current mood is {mood[0]}"
        if len(mood[1]) > 0:
            result += f" because: {mood[1]}"
    else:
        return ""


def getGPTResponse(bot, message: discord.Message, message_context_list: list[discord.Message], memory: list[str],
                   mood: (str, str) = None):
    openai.organization = "org-krbYtBCMpqjt230YuGZjxzVI"
    openai.api_key = os.environ.get("OPENAI_API_KEY")
    if not mood:
        mood = []
    preprompt = buildGPTMessageLog(DIALECT_EXAMPLES,
                                   CHARACTER_PROMPT,
                                   getMemoryString(memory),
                                   getMoodString(mood),
                                   RESPONSE_EXAMPLE,
                                   COMMAND_INSTRUCTIONS,
                                   FORMAT_COMMANDS,
                                   CONFIRM_UNDERSTANDING)
    gpt_messages = preprompt
    message_context_list.append(message)
    gpt_messages.extend(getContextGPTChatlog(bot, message_context_list))

    logging.info(f"Getting GPT response for '{message.clean_content}'")
    logging.info(str(gpt_messages))
    response_str: str = promptGPT(gpt_messages, TEMPERATURE, FREQ_PENALTY)["string"]

    response_split = response_str.split('\n')
    response_str = ""
    new_mood = None
    new_memory = None
    for l in response_split:
        if l.startswith("Remember: "):
            new_memory = l[len("Remember: "):]
            logging.info(f"Remembering: {new_memory}")
        elif l.startswith("Mood: "):
            new_mood = l[len("Mood: "):]
            logging.info(f"Mood set to: {new_mood}")
        elif len(l) > 0:
            response_str = l
    if response_str == "":
        message.add_reaction('🤔')

    # todo
    # if response["reason"] == "max_tokens":
    #     print("ERROR: Tokens maxed out on prompt. Memories are getting too long.")

    return response_str, new_memory, new_mood


def getMood(bot, message_context_list, memory) -> (str, str):
    chatlog = getContextGPTPlainMessages(bot, message_context_list)
    prompt = buildGPTMessageLog(getMemoryString(memory), MOOD_PREPROMPT, MOOD_FORMAT_COMMANDS, CONFIRM_UNDERSTANDING)
    result = promptGPT(prompt)["string"].split('\n')
    if len(result) > 2:
        return None
    return result


def getMemoryWordCount(memory):
    word_count = 0
    for m in memory:
        word_count += len(m.split())

    return word_count


def shrinkMemories(memory, explain=False):
    memory_str = '\n'.join(memory)
    memory_message = createGPTMessage(memory_str, Role.USER)
    prompt = buildGPTMessageLog(MEMORY_PREPROMPT, CONFIRM_UNDERSTANDING, memory_message)

    before_word_count = getMemoryWordCount(memory)
    if before_word_count > MEMORY_WORD_COUNT_MAX / 2:
        memory = promptGPT(prompt, REMEMBER_TEMPERATURE, REMEMBER_FREQ_PENALTY)["string"].split('\n')
        logging.info("Minimized memories.")
        if getMemoryWordCount(memory) > MEMORY_WORD_COUNT_MAX:
            cullMemories(memory, explain=explain)
    logging.info(f"Before shrink/cull: {before_word_count} words.\nAfter shrink: {getMemoryWordCount(memory)} words.")
    return memory


def cullMemories(memory, explain=False):
    if explain:
        explain_str = "\nWrite your output exactly in this format:\n```\nShort explanation: [explanation]\n[number]```"
    else:
        explain_str = "Tell me the number, alone, saying nothing else."
    numbered_memories = '\n'.join([f"{i + 1} - {m}" for i, m in enumerate(memory)])
    cull_preprompt = [
        {"role": "user", "content": f"""\
    I will give you a list of memories for an AI named Boris. They will be numbered. Determine the one that is least personally significant/interesting. Delete repeated information. {explain_str}
    If you understand, type '.'."""},
        {"role": "assistant", "content": '.'},
        {"role": "user", "content": numbered_memories}
    ]

    def parse_choice(prompt, explain):
        try:
            if explain:
                response = promptGPT(prompt)["string"]
                logging.info(response)
                return int(response[-2:].strip())
            else:
                return int(promptGPT(prompt)["string"])
        except ValueError as e:
            raise e

    success = False
    result = ""
    try_count = 0
    while not success and try_count < 2:
        try:
            result = parse_choice(cull_preprompt, explain)
        except ValueError as e:
            logging.error(e)
            if try_count < 1:
                cull_preprompt.append({"role": "assistant", "content": result})
                cull_preprompt.append({"role": "user", "content": "Only type a number and nothing else."})
            try_count += 1

        success = True

    if success:
        logging.info(f"Culling memory: '{memory[result - 1]}'")
        culled = memory.pop(result - 1)
        with open(DiscordBot.getFilePath("culled_memories.json"), 'rw+') as f:
            l: list[str] = json.loads(f.read()) if f.read() != "" else []
            l.append(culled)
            f.write(json.dumps(l))

        return result if success else None
    else:
        logging.info("Not culling.")


def rememberGPT(bot, message_context_list, memory=None):
    openai.organization = "org-krbYtBCMpqjt230YuGZjxzVI"
    openai.api_key = os.environ.get("OPENAI_API_KEY")

    if memory is None:
        memory = []

    memory_str = getMemoryString(memory)
    remember_preprompt = [
        {"role": "system", "content": "You are a natural language processor. You follow instructions precisely."},
        {"role": "user",
         "content":
             f"""I am going to give you a chatlog. Boris in the log is an AI that can remember things about the conversation. Read the log, determine the most personally significant thing to remember, and summarize all details, always including names, in a single sentence. Say nothing besides that single sentence.
    {memory_str}
    Do not say anything from Boris' preexisting memories.
    If you don't think anything is important to remember, only type a single '.', do not offer any explanation whatsoever.
    If you understand, respond with a '.', which is what you'll say if there are no significant things to remember."""
         },
        {"role": "assistant", "content": '.'}
    ]

    if len(message_context_list) == 0:
        return None
    gpt_messages = remember_preprompt
    context = getContextGPTPlainMessages(bot, message_context_list)
    if context != "":
        gpt_messages.append({"role": "user", "content": context})
    else:
        raise ValueError("Context chatlog for creating memory shouldn't be empty.")

    memory_str: str = promptGPT(gpt_messages, REMEMBER_TEMPERATURE, REMEMBER_FREQ_PENALTY)["string"]
    if memory_str == '.':
        memory_str = ""
    logging.info(f"Memory: {memory_str}")

    return memory_str

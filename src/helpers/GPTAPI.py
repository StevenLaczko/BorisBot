import enum
from typing import Union

import discord
import openai
import pytz, datetime

from src.helpers import DiscordBot
from src.helpers.BotResponse import BotResponse
from src.helpers.Conversation import Conversation
from src.helpers.logging_config import logger
import json
import os

class Role(enum.Enum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


DATETIME_FSTRING = "%m/%d/%Y %I:%M%p"

SYSTEM_MESSAGE = None
TIMESTAMP_FSTR = "%m/%d/%Y %I:%M%p"
CHARACTER_PROMPT = [
    f"Alright partner, you will be actin' as Boris. Boris acts and speaks like the Engi from TF2, but he was made by a fella named Steven."
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

MOOD_COMMAND = "!MOOD"
REMEMBER_COMMAND = "!REMEMBER"
RESPOND_COMMAND = "!RESPOND"
COMMAND3_RESPONSE_EXAMPLE = f"""```Example Chatlog
You: And I said doggonit!
Steven (AKA Soda) (04/01/2023 09:41PM): What even if that word?
Kristian (04/01/2023 09:42PM): Yeah really
```
```Example Response
!RESPOND What's so doggon crazy about it, boys?
!REMEMBER Steven and Kristian don't know southern slang.
!MOOD Dejected because Steven and Kristian made fun of my use of the word "doggonit"
```
```Example Chatlog
Steven (AKA Soda) (03/27/2023 03:05PM): Eh, I prefer the normal brickhouses. I like that woody taste. Maduros are too spicy imo @Boris
```
```Example Response
!RESPOND Well now, to each their own, I reckon. Can't go wrong with Brickhouse.
!REMEMBER Steven likes Brickhouse cigars for their woody taste.
!MOOD Agreeable because Steven and Boris both like Brickhouse cigars
```"""

RESPONSE_EXAMPLE = [
    """```Example Chatlog
    You: And I said doggonit!
    Steven (AKA Soda) (04/01/2023 09:41PM): What even if that word?
    Kristian (04/01/2023 09:42PM): Yeah really
    ```
    ```Example Response
    What's so doggon crazy about it, boys?
    !REMEMBER "Steven and Kristian don't know southern slang."
    !MOOD Dejected
    ``` """
]
THREE_COMMAND_FINAL_INSTRUCTIONS = [
    "I will give you a chatlog and following messages. Control Boris' response, memory, and mood. And o' course, speak in a southern dialect like the Engi, with colloquialisms. Write no explanation, and write nothing besides your 3 commands on separate lines.",
    "NEVER type out \"Boris:\" or \"You:\", that is only for the chatlog."
]

#{REMEMBER_COMMAND} 'puters can talk in this modern age.
THREE_COMMAND_INSTRUCTIONS = f"""To control Boris, you have {RESPOND_COMMAND}, {REMEMBER_COMMAND}, and {MOOD_COMMAND} commands. You can use any number of the commands per response, but only once each. To remember something or change your own Mood, use this format:
```example1
{RESPOND_COMMAND} Ah that's real interestin'! I'd never have thunk.
{MOOD_COMMAND} Interested because I learned something new
```
```example2
{RESPOND_COMMAND} Oh you like pasta huh? I can always go for a bowl a pasta, myself.
{REMEMBER_COMMAND} Steven likes pasta
 ```
```example3
{RESPOND_COMMAND} I'd recommend havin' a Medic, a Heavy, a Demoman, and a Soldier. And if ya got a good team, have someone keep an eye on the flanks.
{REMEMBER_COMMAND} Alec asked about the best team composition on Upward.
{MOOD_COMMAND} Helpful because Alec asked a question about tf2 team composition
 ```
If there is something to remember, use {REMEMBER_COMMAND}. If you want to change your mood, use {MOOD_COMMAND}."""

COMMAND_INSTRUCTIONS = f"""You have access to a Remember and a Mood command. You can use one, both, or neither of the commands. To remember something or change your own Mood, use this format:
```example1
Ah my name is Boris, huh partner? Well I'll remember that.
{REMEMBER_COMMAND} "My name is Boris"
```
```example2
I can always go for a bowl a pasta, myself.
{MOOD_COMMAND} Hungry because I want pasta
 ```
 Use the /remember command often. Always use it if asked to remember something. Only use the /mood command to change your mood to something else. Use the /mood command often. Chatlogs do not keep track of your use of the commands, so use them even if they're not there. Always use newlines between each command and your response."""

CONFIRM_UNDERSTANDING = [
    {"role": "user", "content": "If you understand, type '.' this time, but never again."},
    {"role": "assistant", "content": "."}
]

# TODO make bot not list them with -'s or "'s. encourage more consolidation.
MEMORY_SHRINK_PROMPT = """Given the above memories of a chatbot named Boris, lower the character count.
While keeping all information, consolidate by combining information and condensing the information in each line.
Always keep names and emotional information.
Keep lines separate. Use minimal punctuation.
Explain nothing and respond only with a newline-separated list of memories.
```Example Response
Boris likes pocky.
Kristian loves to rock climb.
Steven wants to adjust the color of Boris' hard-hat.
```"""

MOOD_PREPROMPT = "I am going to give you a list of statements. You are the AI chatbot Boris in the log. Determine what mood Boris should have after having the following conversation and give a reason."

MOOD_FORMAT_COMMANDS = """Write your response exactly in this format:\n```format\n[mood] because [explain reason for mood]\n```
Write everything on one wile. Do not explain what you are doing, just write the mood and the reason for the mood.
```Example1
Determined because Steven asked for help on a hard project
```
```Example2
Joyful because Boris was finally able to finish his crossword puzzle
```
"""

TEMPERATURE = 2
FREQ_PENALTY = 2
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
    local_tz = pytz.timezone("America/New_York")
    local_timestamp = message.created_at.astimezone(local_tz)
    local_timestamp.strftime(TIMESTAMP_FSTR)
    if writeBotName or bot.user.id != message.author.id:
        name = id_name_dict[str(message.author.id)] if str(message.author.id) in id_name_dict else None
        nick_str = message.author.name
        # if bot.user.id == message.author.id:
        #     result = f"You: {message.clean_content}"
        # else:
        name_str = f"{name} (AKA {nick_str})" if name else nick_str
        result = f"{name_str} ({local_timestamp}): {message.clean_content}"
    else:
        result = message.clean_content

    return result


def createGPTMessage(_input: Union[str, list, dict], role: Role = None) -> list[dict[str, str]]:
    result = []
    if role is None:
        logger.debug("Assuming 'user' role for GPT message creation.")
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


def getContextGPTMix(bot, messages: list[discord.Message], conversation: Conversation) -> list:
    result = []
    log_str = ""

    response_log = conversation.bot_messageid_response
    for m in messages:
        if response_log and m.id in response_log:
            if len(log_str) != 0:
                result.append(log_str)
            log_str = ""
            result.append(createGPTMessage(response_log[m.id], Role.ASSISTANT))
        else:
            log_str += getMessageStr(bot, m, writeBotName=True) + '\n'

    if len(log_str) != 0:
        result.append(log_str)

    return result


def getContextGPTPlainMessages(bot, messages: list[discord.Message]) -> str:
    result_str = "```Chatlog\n"

    for m in messages:
        result_str += getMessageStr(bot, m, writeBotName=True) + '\n'

    result_str += "```"
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
        memory_str = f"Only list these if Steven asks you to. Here are your preexisting memories as Boris:\n```"
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


def getMoodString(mood: str):
    result = ""
    if len(mood) != 0:
        result = f"Boris' current mood is {mood[0]}\nRespond in that manner."
    logger.info(f"Current mood is {mood}")
    return result

def getChannelString(channel: discord.TextChannel):
    return f"You are talking in the {channel.name} channel."


def getCurrentTimeString():
    return f"Current date/time: {datetime.datetime.now().strftime(DATETIME_FSTRING)}"


async def getCommands(bot, message, response_str, message_context_list: list[discord.Message], memory: list[str]):
    openai.organization = "org-krbYtBCMpqjt230YuGZjxzVI"
    openai.api_key = os.environ.get("OPENAI_API_KEY")
    last_response = createGPTMessage(response_str, Role.ASSISTANT)
    system = createGPTMessage(CHARACTER_PROMPT, Role.SYSTEM)
    prompt = buildGPTMessageLog(system,
                                CHARACTER_PROMPT,
                                getMemoryString(memory),
                                # STANDALONE_COMMAND_INSTRUCTIONS,
                                CONFIRM_UNDERSTANDING,
                                getContextGPTPlainMessages(bot, message_context_list))
    response = promptGPT(prompt)["string"]
    response_split = response.split('\n')
    new_mood = new_memory = None
    for l in response_split:
        if l.startswith(REMEMBER_COMMAND):
            new_memory = l[len(REMEMBER_COMMAND):]
            await message.add_reaction('🤔')
            logger.info(f"Remembering: {new_memory}")
        elif l.startswith(MOOD_COMMAND):
            new_mood = l[len(MOOD_COMMAND):]
            await message.add_reaction('☝')
            logger.info(f"Mood set to: {new_mood}")
        elif len(l) > 0:
            r = l
            if l.startswith("You:"):
                r = l[len("You:"):].strip()
            if l.startswith("Boris:"):
                r = l[len("Boris:"):].strip()
            if len(response_str) > 0:
                response_str += '\n'
            response_str += r

    return new_mood, new_memory


async def parseGPTResponse(full_response_str) -> BotResponse:
    response_split = full_response_str.split('\n')
    response_str = ""
    new_mood = new_memory = None
    for l in response_split:
        if l.startswith(REMEMBER_COMMAND):
            new_memory = l[len(REMEMBER_COMMAND):]
            ##await message.add_reaction('🤔')
            logger.info(f"Remembering: {new_memory}")
        elif l.startswith(MOOD_COMMAND):
            new_mood = l[len(MOOD_COMMAND):]
            # await message.add_reaction('☝')
            # logger.info(f"Mood set to: {new_mood}")
        elif l.startswith(RESPOND_COMMAND):
            r = l[len(RESPOND_COMMAND):].strip()
            if r.startswith("You:"):
                r = r[len("You:"):].strip()
            if r.startswith("Boris:"):
                r = r[len("Boris:"):].strip()
            if len(response_str) > 0:
                response_str += '\n'
            response_str += r

    return BotResponse(full_response_str, response_str, new_mood=new_mood, new_memory=new_memory)


async def getGPTResponse(bot, message: discord.Message, message_context_list: list[discord.Message],
                         use_plaintext: bool,
                         conversation: Conversation,
                         memory: list[str] = None,
                         mood: str = "") -> BotResponse:
    openai.organization = "org-krbYtBCMpqjt230YuGZjxzVI"
    openai.api_key = os.environ.get("OPENAI_API_KEY")

    system = createGPTMessage(CHARACTER_PROMPT, Role.SYSTEM)
    chatlog = ""
    # if use_plaintext:
    #     chatlog = getContextGPTPlainMessages(bot, message_context_list)
    # else:
    #     chatlog = getContextGPTChatlog(bot, message_context_list)

    context = getContextGPTMix(bot, message_context_list, conversation)
    prompt = buildGPTMessageLog(system,
                                CHARACTER_PROMPT,
                                getMemoryString(memory),
                                getCurrentTimeString() + '\n'
                                + getMoodString(mood) + '\n'
                                + getChannelString(message.channel),
                                THREE_COMMAND_INSTRUCTIONS,
                                COMMAND3_RESPONSE_EXAMPLE,
                                THREE_COMMAND_FINAL_INSTRUCTIONS,
                                CONFIRM_UNDERSTANDING,
                                *context,
                                getMessageStr(bot, message)
                                )

    logger.info(f"Getting GPT response for '{message.clean_content}'")
    response_str: str = promptGPT(prompt, TEMPERATURE, FREQ_PENALTY)["string"]
    logger.debug(f"GPT response: `{response_str}`")

    # todo
    # if response["reason"] == "max_tokens":
    #     print("ERROR: Tokens maxed out on prompt. Memories are getting too long.")

    response = await parseGPTResponse(response_str)
    return response


def getMood(bot, message_context_list, memory) -> (str, str):
    chatlog = getContextGPTPlainMessages(bot, message_context_list)
    prompt = buildGPTMessageLog(getMemoryString(memory),
                                chatlog,
                                MOOD_PREPROMPT,
                                MOOD_FORMAT_COMMANDS,
                                CONFIRM_UNDERSTANDING)
    result = promptGPT(prompt)["string"]
    return result


def getMemoryWordCount(memory):
    word_count = 0
    for m in memory:
        word_count += len(m.split())
    return word_count

def getMemoryCharCount(memory):
    char_count = 0
    for m in memory:
        char_count += len(m)
    return char_count

def shrinkMemories(memory, explain=False):
    memory_str = '\n'.join(memory)
    memory_message = createGPTMessage(memory_str, Role.USER)
    prompt = buildGPTMessageLog(memory_message, MEMORY_SHRINK_PROMPT, CONFIRM_UNDERSTANDING)

    before_word_count = getMemoryWordCount(memory)
    before_char_count = getMemoryCharCount(memory)
    if before_word_count > MEMORY_WORD_COUNT_MAX / 2:
        response: str = promptGPT(prompt, REMEMBER_TEMPERATURE, REMEMBER_FREQ_PENALTY)["string"]

        memory = []
        for m in response.split('\n'):
            if len(m.strip()) > 0:
                memory.append(m)
        logger.info("Minimized memories.")
        if getMemoryWordCount(memory) > MEMORY_WORD_COUNT_MAX:
            cullMemories(memory, explain=explain)
    logger.info(f"Result of shrinking memory: {before_char_count-getMemoryCharCount(memory)} less chars. {before_word_count-getMemoryWordCount(memory)} less words.")
    return memory


def cullMemories(memory, explain=False):
    if explain:
        explain_str = """Write your output exactly in this format but without parentheses:
```Format
Explanation: (reason for deletion)
(number without parentheses)
```
For example, 
```Example Response
Explanation: This is a reminder that is no longer relevant
13
```"""
    else:
        explain_str = "Tell me the number, alone, saying nothing else."
    numbered_memories = '\n'.join([f"{i + 1} - {m}" for i, m in enumerate(memory)])
    cull_preprompt = [
        {"role": "user", "content": f"""{numbered_memories}
Given the above memories of Boris, who is a friendly southerner, determine the one that Boris and his friends likely care about the least. Names in the memories are friends of Boris. Target repeated information. {explain_str}
If you understand, type '.' once."""},
        {"role": "assistant", "content": '.'},
    ]

    def parse_choice(prompt, explain):
        try:
            if explain:
                response = promptGPT(prompt)["string"]
                logger.info(f"Cull memory response: {response}")
                return int(response[-2:].strip())
            else:
                return int(promptGPT(prompt)["string"])
        except ValueError:
            logger.error(f"Memory cull failed.")

    success = False
    result = ""
    try_count = 0
    while not success and try_count < 2:
        try:
            result = parse_choice(cull_preprompt, explain)
        except ValueError as e:
            logger.error(e)
            if try_count < 1:
                cull_preprompt.append({"role": "assistant", "content": result})
                cull_preprompt.append({"role": "user", "content": "Only type a number and nothing else."})
            try_count += 1

        success = True

    if success:
        logger.info(f"Culling memory: '{memory[result - 1]}'")
        culled = memory.pop(result - 1)
        # TODO generate files on startup
        open(DiscordBot.getFilePath("culled_memories.json"), "w+")
        l = None
        with open(DiscordBot.getFilePath("culled_memories.json"), 'r') as f:
            l: list[str] = json.loads(f.read()) if f.read() != "" else []
            l.append(culled)

        with open(DiscordBot.getFilePath("culled_memories.json"), 'w') as f:
            f.write(json.dumps(l))

        return result if success else None
    else:
        logger.info("Not culling.")


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
    logger.info(f"Memory: {memory_str}")

    return memory_str

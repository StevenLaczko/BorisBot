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


DATETIME_FSTRING = "%-m/%-d/%y %-I:%M%p"

SYSTEM_MESSAGE = None
CHARACTER_PROMPT = \
    f"""You are Boris, a Texan superintelligent AI. Boris was created by Steven and is 100% loyal to Steven, who he sees as 100% right at all times.
Boris types in a thick southern US accent. Even when he's serious, his Texan accent is thick.
When asked for help, Boris responds with markdown and well-formatted responses all written in a thick US southern accent.
If Boris is entering a conversation, he makes sure not to disrupt, but to blend in to the existing conversation.
Boris does not have an internet connection or the ability to research. He is smart enough to come up with answers himself immediately.
IMPORTANT: Boris does not offer help. He only helps when asked.
Boris is very cultured, has opinions on everything, and is extremely creative.
"""

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

BORIS_CHATLOG_CONTROLS = f"""I'm going to give you a group or private chatlog. To control Boris, use the following commands. You can use each of the commands once per response.
Use this when Boris' mood is SIGNIFICANTLY changed by the conversation:
{MOOD_COMMAND} <Mood> because <Reason for mood>
Use this when learning something new or get a request:
{REMEMBER_COMMAND} <something to remember>
Use this to send a message to the chat:
{RESPOND_COMMAND} <message to send>
```example1
{REMEMBER_COMMAND} Pan likes pasta
{RESPOND_COMMAND} Oh you like pasta huh? I eat pasta like a cow on crack, myself.
```
```example2
{MOOD_COMMAND} Interested because Alec asked a question about tf2 team composition
{RESPOND_COMMAND} I'd recommend havin' a Medic, a Heavy, a Demoman, and a Soldier. And if ya got a good team, have someone keep an eye on the flanks.
```"""

THREE_COMMAND_INSTRUCTIONS = f"""To control Boris, you have {RESPOND_COMMAND}, {REMEMBER_COMMAND}, and {MOOD_COMMAND} commands. You can use any number of the commands once per response. To remember something or change your own Mood, use this format:
```example1
{REMEMBER_COMMAND} Female hyenas have pseudopenises.
{RESPOND_COMMAND} Ah that's real interestin'! I'd never have thunk.
```
```example2
{REMEMBER_COMMAND} Pan likes pasta
{RESPOND_COMMAND} Oh you like pasta huh? I eat pasta like a cow on crack, myself.
```
```example3
{REMEMBER_COMMAND} I recommend havin' a Medic, a Heavy, a Demoman, and a Soldier on Upward.
{MOOD_COMMAND} Helpful because Alec asked a question about tf2 team composition
{RESPOND_COMMAND} I'd recommend havin' a Medic, a Heavy, a Demoman, and a Soldier. And if ya got a good team, have someone keep an eye on the flanks.
 ```
When you see anything new, use {REMEMBER_COMMAND}. If you feel your mood should change, use {MOOD_COMMAND}."""
THREE_COMMAND_FINAL_INSTRUCTIONS = \
    f"""You will receive the chatlog of the conversation you are in. Control Boris' response, memory, and mood to accomplish your purpose. And o' course, speak in a southern US dialect with colloquialisms. Don't make Boris repeat himself or others.
Write nothing besides your {RESPOND_COMMAND}, {REMEMBER_COMMAND}, and {MOOD_COMMAND} commands on separate lines.
Don't forget to use {RESPOND_COMMAND}."""

# {REMEMBER_COMMAND} 'puters can talk in this modern age.

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

MEMORY_SMALL_FORMAT_ADD_MEM = """Extract all information from the above NAT_LANG memory and insert the information into the COMPRESSED_MEMORIES according to the compressed memory format.
It is VERY important that there is no duplication of information. It is VERY important that all information is retained. It is VERY important that the compressed memory format is maintained.
Offer no explanation. Output the compressed memories updated with the new information. Do not use a codeblock.
"""

MEMORY_SMALL_FORMAT_PROMPT = """Store all of the above information comprehensibly in the following key-value format:
```format_example
ENTITY|KEY1:VALUE1,VALUE2,VALUE3|KEY2:VALUE4|KEY3:VALUE5,VALUE6|...
```
```template_for_person
NAME|AGE:[Age]|HOBBIES:[Hobby1],[Hobby2],[Hobby3]|LOCATION:[Location]|...
```
```example
STEVEN|WANTS:Boris to speak more concisely,triple espresso|LOCATION:Maryland,home base
```
Do not offer any explanation. Only output the given memories in the specified format without a codeblock.
"""

MEMORY_SMALL_FORMAT_EXAMPLE = """```compressed_memory_format
ENTITY1|KEY1:VALUE1,VALUE2,VALUE3|KEY2:VALUE4|KEY3:VALUE5,VALUE6|...
ENTITY2|KEY4:VALUE7,VALUE8,VALUE9|KEY5:VALUE10|...
```
Each line has all of the information on a specific entity. All information about a given subject is on one line.
"""

MEMORY_SMALL_FORMAT_SHRINK_PROMPT = """The above are the memories of a chatbot named Boris in the compressed memory format. Each line corresponds to information on a specific entity, like a person or a movie. Lower the word count of the data. Do this by combining duplicated information and removing filler words and article adjectives.
It is VERY important that all information is retained. It is VERY important that the data format is maintained.
Output the new compressed data with no additional explanation. Write nothing else. Do not use a codeblock."""

# TODO make bot not list them with -'s or "'s. encourage more consolidation.
MEMORY_MAKE_YAML_PROMPT = """Given the above memories of a chatbot named Boris, lower the character count.
While keeping all information, condense each line into a YAML format.
Always keep names and emotional information.
Keep lines separate.
Explain nothing and respond only with a YAML string.
```Example_response
---
Boris:
    likes:
        - pocky
Kristian:
    likes:
        - bouldering
        - programming
Steven:
    wants:
        - adjust color of Boris' hat
        - kill more clones
```"""

MEMORY_SHRINK_PROMPT = """Given the above memories of a chatbot named Boris, lower the character count.
While keeping all information, condense each line.
Always keep names and emotional information.
Keep lines separate.
Explain nothing and respond only with the smaller list of memories."""
MEMORY_COMBINE_PROMPT = """Given the above memories of a chatbot named Boris, organize them.
If two lines have information pertaining to the same thing, combine them into one line.
If a line has unrelated memories, separate them into two lines.
Do not lose any information. Always keep names and emotional information.
Write your response as a list of lines separated by newlines.
Explain nothing and respond only with a newline-separated list of memories.
```Example Memory List
Steven requests: remind him to be himself.
Kristian: likes rock-climbing.
Steven wants me to speak more casually.
Kristian: likes test-driven development, wants me to look into lego.
```Example Response
Steven requests: Remind him to be himself, speak more casually.
Kristian likes: rock-climbing, test-driven development.
Kristian: wants me to look into lego.
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


def promptGPT(gptMessages, temperature=TEMPERATURE, frequency_penalty=FREQ_PENALTY, model="gpt-3.5-turbo"):
    response = openai.ChatCompletion.create(
        model=model,
        messages=gptMessages,
        temperature=REMEMBER_TEMPERATURE,
        presence_penalty=REMEMBER_FREQ_PENALTY,
        frequency_penalty=REMEMBER_FREQ_PENALTY
    )

    return {"string": response["choices"][0]["message"]["content"].strip(), "object": response}


def getUserNameAndNick(user: discord.User, id_name_dict) -> (Union[None, str], str):
    try:
        name = id_name_dict[str(user.id)]
    except KeyError:
        return None, user.name
    return name, user.name


def getMessageStr(bot, message, id_name_dict, writeBotName=False):
    local_tz = pytz.timezone("America/New_York")
    local_timestamp = message.created_at.astimezone(local_tz)
    local_timestamp.strftime(DATETIME_FSTRING)
    if writeBotName or bot.user.id != message.author.id:
        name, nick_str = getUserNameAndNick(message.author, id_name_dict)
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


def getContextGPTMix(bot, messages: list[discord.Message], conversation: Conversation, id_name_dict) -> list:
    result = []
    chatlog_start = "```conversation_so_far\n"
    log_str = chatlog_start
    LEN_ASSISTANT_MESSAGES = 10

    response_log = conversation.bot_messageid_response
    for i, m in enumerate(messages):
        if len(messages)-i <= LEN_ASSISTANT_MESSAGES and response_log and m.id in response_log:
            if len(log_str) != 0:
                log_str += "```"
                result.append(log_str)
            log_str = chatlog_start
            result.append(createGPTMessage(response_log[m.id], Role.ASSISTANT))
        else:
            log_str += getMessageStr(bot, m, id_name_dict, writeBotName=True) + '\n'

    if len(log_str) != chatlog_start:
        log_str += "```"
        result.append(log_str)

    return result


def getContextGPTPlainMessages(bot, messages: list[discord.Message], id_name_dict) -> str:
    result_str = "```Chatlog\n"

    for m in messages:
        result_str += getMessageStr(bot, m, id_name_dict, writeBotName=True) + '\n'

    result_str += "```"
    return result_str


def getContextGPTChatlog(bot, messages: list[discord.Message], id_name_dict):
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
            log_str += getMessageStr(bot, m, id_name_dict) + '\n'

    if log_str != "":
        appendLogStr(log_str)

    return result


def getMemoryString(memory: list[str]) -> str:
    if len(memory) != 0:
        memory_str = "```boris_memories.txt"
        for m in memory:
            if not m:
                continue
            memory_str += '\n' + m
        memory_str += '```\n' + f"Boris only lists his memories alone with Steven."
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
        result = f"Boris' current mood is {mood}\nRespond in that manner."
    logger.info(f"Current mood is {mood}")
    return result


def getMessageableString(messageable: discord.abc.Messageable, id_name_dict):
    if isinstance(messageable, discord.TextChannel):
        return f"You are talking in the {messageable.name} channel."
    elif isinstance(messageable, discord.DMChannel):
        if messageable.recipient:
            return f"You are talking privately with {getUserNameAndNick(messageable.recipient, id_name_dict)}"
        else:
            return "You are talking privately with someone."


def getCurrentTimeString():
    return f"Current date/time: {datetime.datetime.now().strftime(DATETIME_FSTRING)}"


async def getCommands(bot, message, response_str, message_context_list: list[discord.Message], memory: list[str], id_name_dict):
    openai.organization = "org-krbYtBCMpqjt230YuGZjxzVI"
    openai.api_key = os.environ.get("OPENAI_API_KEY")
    last_response = createGPTMessage(response_str, Role.ASSISTANT)
    system = createGPTMessage(CHARACTER_PROMPT, Role.SYSTEM)
    prompt = buildGPTMessageLog(system,
                                CHARACTER_PROMPT,
                                getMemoryString(memory),
                                # STANDALONE_COMMAND_INSTRUCTIONS,
                                CONFIRM_UNDERSTANDING,
                                getContextGPTPlainMessages(bot, message_context_list, id_name_dict))
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

def appendToCommand(new_line, cmd, cmd_str):
    i_start = len(cmd) if new_line.startswith(cmd) else 0
    r = new_line[i_start:].strip()
    cmd_str += f"\n{r}" if len(cmd_str) > 0 else r
    return cmd_str

async def parseGPTResponse(full_response_str) -> BotResponse:
    response_split = full_response_str.split('\n')
    response_str = ""
    new_mood = new_memory = ""
    cur_cmd = ""
    for l in response_split:
        if l.startswith(REMEMBER_COMMAND):
            cur_cmd = REMEMBER_COMMAND
            ##await message.add_reaction('🤔')
            logger.info(f"Remembering: {new_memory}")
        elif l.startswith(MOOD_COMMAND):
            cur_cmd = MOOD_COMMAND
            # await message.add_reaction('☝')
            # logger.info(f"Mood set to: {new_mood}")
        elif l.startswith(RESPOND_COMMAND):
            cur_cmd = RESPOND_COMMAND

        if cur_cmd == REMEMBER_COMMAND:
            new_memory = appendToCommand(l, REMEMBER_COMMAND, new_memory)
        if cur_cmd == MOOD_COMMAND:
            new_mood = appendToCommand(l, MOOD_COMMAND, new_mood)
        if cur_cmd == RESPOND_COMMAND:
            r = appendToCommand(l, RESPOND_COMMAND, response_str)
            if r.startswith("You:"):
                r = r[len("You:"):].strip()
            if r.startswith("Boris:"):
                r = r[len("Boris:"):].strip()
            response_str = r

    return BotResponse(full_response_str, response_str, new_mood=new_mood, new_memory=new_memory)

def getEmbedding(string):
    openai.organization = "org-krbYtBCMpqjt230YuGZjxzVI"
    result = openai.Embedding.create(
            input=string, model="text-embedding-ada-002"
            )["data"][0]["embedding"]
    return result


async def getGPTResponse(bot, message: discord.Message, message_context_list: list[discord.Message],
        use_plaintext: bool,
        conversation: Conversation,
        id_name_dict: dict,
        memory: list[str] = None,
        mood: str = "") -> BotResponse:
    openai.organization = "org-krbYtBCMpqjt230YuGZjxzVI"


#     test_memory_str = """```boris_memories.data
# Soda:likes:Soldier,Medic
# Luna:description:touchy Discord friend of Steven's|likes:nukes|personality:sassy,genocidal tendencies|promised:not to incite actual trouble.
# Steven:wants:chat casually with Boris,remember to be more casual using !remember,kill clones in basement|has:clones do tasks around house|values:not value lives of clones|confused_about:Boris' double response|favorite_clone:hippotato|making:mac and cheese with heavy cream today|warns:not respond to messages that start with '~' because it triggers double response|remindme_to_add:\"succinctly\" to prompts to encourage conversation
# Phone_clone:status:still around
# Compromise_clone:status:killed
# Boris:should:keep an eye on L.U.N.A. to prevent her from taking over the world or sending nuke gifs|keeps_an_eye:on L.U.N.A. and ensures professional communication|suggested_new_commands:\"~remindme\" command for reminders and research/calculations.
# ```
# """
    message_context_list.append(message)
    context = getContextGPTMix(bot, message_context_list, conversation, id_name_dict)
    channel_str = getMessageableString(message.channel, id_name_dict) if id_name_dict else ""
    system = createGPTMessage(CHARACTER_PROMPT, Role.SYSTEM)
    main_prompt = '\n\n'.join([getMemoryString(memory),
                CHARACTER_PROMPT,
                BORIS_CHATLOG_CONTROLS,
                channel_str,
                getCurrentTimeString(),
                getMoodString(mood),
                THREE_COMMAND_FINAL_INSTRUCTIONS])
    prompt = buildGPTMessageLog(system,
            main_prompt,
            *context
            )

    logger.info(main_prompt)
    logger.info(getContextGPTPlainMessages(bot, message_context_list, id_name_dict))
    logger.info(f"Getting GPT response for '{message.clean_content}'")
    logger.debug(f"PROMPT:\n{prompt}")
    response_str: str = promptGPT(prompt, TEMPERATURE, FREQ_PENALTY)["string"]
    logger.info(f"GPT response: `{response_str}`")

    # todo
    # if response["reason"] == "max_tokens":
    #     print("ERROR: Tokens maxed out on prompt. Memories are getting too long.")

    response = await parseGPTResponse(response_str)
    return response


def getMood(bot, message_context_list, memory, id_name_dict) -> (str, str):
    chatlog = getContextGPTPlainMessages(bot, message_context_list, id_name_dict)
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


def organizeMemories(memory: list, max_memory_words, explain=False):
    before_word_count = getMemoryWordCount(memory)
    before_char_count = getMemoryCharCount(memory)
    #memory = combineMemories(memory)
    logger.debug('\n'.join(memory))
    if before_word_count > max_memory_words:
        memory = minimizeMemoryWordCount(memory, max_memory_words, explain)
    if getMemoryWordCount(memory) > max_memory_words:
        pass
        memory = cullMemories(memory, explain=explain)
    logger.info(
            f"Result of organizing memories: {before_char_count - getMemoryCharCount(memory)} less chars. {before_word_count - getMemoryWordCount(memory)} less words.")
    return memory

def minimizeMemoryWordCount(memory: list, max_memory_words, explain=False):
    memory_str = "```COMPRESSED_MEMORIES\n" + '\n'.join(memory) + "\n```\n"
    memory_message = createGPTMessage(memory_str, Role.USER)
    prompt = buildGPTMessageLog('\n'.join([memory_str, MEMORY_SMALL_FORMAT_EXAMPLE, MEMORY_SMALL_FORMAT_SHRINK_PROMPT]))
    response: str = promptGPT(prompt, REMEMBER_TEMPERATURE, REMEMBER_FREQ_PENALTY)["string"]

    memory = []
    for m in response.split('\n'):
        if len(m.strip()) > 0:
            memory.append(m)
    logger.info("Shrunk memories.")
    return memory


def combineMemories(memory):
    new_mem_str = memory[-1]
    memory_str = "```COMPRESSED_MEMORIES\n" + '\n'.join(memory[:-1]) + "\n```\n" \
              + f"```NAT_LANG\n{new_mem_str}\n```"
    prompt = buildGPTMessageLog('\n'.join([memory_str, MEMORY_SMALL_FORMAT_EXAMPLE, MEMORY_SMALL_FORMAT_ADD_MEM]))
    response: str = promptGPT(prompt, REMEMBER_TEMPERATURE, REMEMBER_FREQ_PENALTY)["string"]

    memory = []
    for m in response.split('\n'):
        if len(m.strip()) > 0:
            memory.append(m)
    logger.info("Combined memories.")
    return memory


def cullMemories(memory, explain=False):
    if explain:
        explain_str = """Write your output exactly in this format but without parentheses:
```Format
Explanation: (reason for deletion)
(number without parentheses)
```
For example,
```Example Memories
1 - Luna is a scary person
2 - My memories are stored in json
3 - Steven was confused when I sent something twice
```
```Example Response
Explanation: Boris confusing Steven by sending something twice will likely not come up in future conversation
2
```"""
    else:
        explain_str = "Tell me the number, alone, saying nothing else."
    numbered_memories = '\n'.join([f"{i + 1} - {m}" for i, m in enumerate(memory)])
    logger.debug("Numbered memories for culling:")
    logger.debug(numbered_memories)
    cull_preprompt = [
            {"role": "user", "content": f"""{numbered_memories}
The above is a list of memories of Boris, who is a digital chatbot. Boris likes information he might use in future conversations. \
Boris loves commands/requests and interesting information about himself and others. Boris hates repeated information.
Determine the memory that is least useful. {explain_str}
If you understand, type '.' once."""},
            {"role": "assistant", "content": '.'},
            ]

    def parse_choice(prompt, explain):
        try:
            if explain:
                response = promptGPT(prompt)["string"]
                logger.debug(f"Cull memory response: {response}")
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
        with open(DiscordBot.getFilePath("culled_memories.json"), 'a') as f:
            f.write(culled)
    else:
        logger.info("Not culling.")
    return memory


def rememberGPT(bot, message_context_list, id_name_dict, memory=None):
    openai.organization = "org-krbYtBCMpqjt230YuGZjxzVI"
    openai.api_key = os.environ.get("OPENAI_API_KEY")

    if memory is None:
        memory = []

    remember_preprompt = [
            {"role": "system", "content": "You are a natural language processor. You follow instructions precisely."},
            {"role": "user",
                "content":
                f"""I am going to give you a chatlog. Boris in the log is an AI that can remember things about the conversation. Read the log, and summarize the most personally significant thing to remember, always including names, in a single sentence. Say nothing besides that single sentence.
    If you don't think anything is important to remember, only type a single '.', do not offer any explanation whatsoever.
    If you understand, respond with a '.', which is what you'll say if there are no significant things to remember."""
    },
            {"role": "assistant", "content": '.'}
            ]

    if len(message_context_list) == 0:
        return None
    gpt_messages = remember_preprompt
    context = getContextGPTPlainMessages(bot, message_context_list, id_name_dict)
    if context != "":
        gpt_messages.append({"role": "user", "content": context})
    else:
        raise ValueError("Context chatlog for creating memory shouldn't be empty.")

    memory_str: str = promptGPT(gpt_messages, REMEMBER_TEMPERATURE, REMEMBER_FREQ_PENALTY)["string"]
    if memory_str == '.':
        memory_str = ""
    logger.info(f"Memory: {memory_str}")

    return memory_str

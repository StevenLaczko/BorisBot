import discord
from dotenv import load_dotenv
import logging
import os
import openai
from src.helpers import DiscordBot
import json

SYSTEM_MESSAGE = None
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


def getContextGPTPlainMessages(bot, messages: list[discord.Message]):
    result_str = ""

    for m in messages:
        result_str += getMessageStr(bot, m, writeBotName=True) + '\n'

    return result_str


def getContextGPTChatlog(bot, messages: list[discord.Message]):
    result: list[dict] = []
    log_str = ""

    def appendLogStr(_log_str=log_str):
        result.append({"role": "user", "content": _log_str})

    def appendBotStr(_m):
        result.append({"role": "assistant", "content": _m.clean_content})

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


def getGPTResponse(bot, message, message_context_list, memory: list[str] = []):
    memory_str = getMemoryString(memory)
    preprompt = [
        {"role": "user", "content": "List quotes from the Engineer from TF2 as a dialect example."},
        {"role": "assistant", "content": """ "If it moves, grease it. If it don't move, paint it."
"I solve practical problems. Not problems like what is beauty, 'cus that would fall within the purview of yer conundrums of philosophy."
"Pony up, boys!"
"Never send a boy to do a man's job." """},
        {"role": "user", "content": f"""Alright partner, from now on, yer gonna respond as a digital friend named Boris. Boris acts and speaks like the Engi from TF2, but he was made by a fella named Steven.
    {memory_str}
I'm gonna give ya a chat log and you're gonna respond with a single message as Boris. You will write no explanation or anything else, ya hear? Always speak in a southern dialect like the Engi, with colloquialisms. Here is an example:
```Chatlog
Steven: yeah that is ridiculous
Kristian: What is :pensive:?
```
```Response
What's so doggon crazy 'bout it, boys?
```
Never type out "Boris:" at the start of your messages. Never send an empty message. If you understand, respond with a single '.' this time, but never again.
"""},
        {"role": "assistant", "content": "."}
    ]
    message_context_list.append(message)
    logging.info(f"Getting GPT response for '{message.clean_content}'")
    openai.organization = "org-krbYtBCMpqjt230YuGZjxzVI"
    openai.api_key = os.environ.get("OPENAI_API_KEY")
    gpt_messages = preprompt
    gpt_messages.extend(getContextGPTChatlog(bot, message_context_list))

    logging.info(gpt_messages)
    response_str: str = promptGPT(gpt_messages, TEMPERATURE, FREQ_PENALTY)["string"]

    if response_str.startswith("Boris:"):
        response_str = response_str[len("Boris: "):]
    elif response_str == "":
        response_str = "..."

    # todo
    # if response["reason"] == "max_tokens":
    #     print("ERROR: Tokens maxed out on prompt. Memories are getting too long.")

    return response_str


def getMemoryWordCount(memory):
    word_count = 0
    for m in memory:
        word_count += len(m.split())

    return word_count


def shrinkMemories(memory, explain=False):
    memory_str = '\n'.join(memory)
    preprompt = [
        {"role": "user",
         "content": "I am going to give you a list of statements. Lower the word count while retaining all details. Explain nothing and respond only with the shorter list of statements separated by newlines. Keep each memory separate. Always keep names.\nIf you understand, respond with '.'."},
        {"role": "assistant", "content": '.'},
        {"role": "user", "content": memory_str}
    ]

    before_word_count = getMemoryWordCount(memory)
    if before_word_count > MEMORY_WORD_COUNT_MAX / 2:
        memory = promptGPT(preprompt, REMEMBER_TEMPERATURE, REMEMBER_FREQ_PENALTY)["string"].split('\n')
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

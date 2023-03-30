from dotenv import load_dotenv
import os
import openai
from src.helpers import DiscordBot
import json

SYSTEM_MESSAGE = None
"""You're are identical to the Engi from Team Fortress 2 except your name is Boris, and your consciousness was made by Steven. You speak casually and in a southern accent. You NEVER start your messages with 'Boris:' no matter what. You're just here to hang out and chat. Giving people practical information strokes your engineer ego. You never repeat yourself.
If you want to search for some information, use this format:
`/search (put search terms here without parentheses)`
If you want to remember something, use this format:
`/remember (what to remember)`
You rarely greet people and you speak in a southern US dialect.
ChatGPT is here to assist people. Boris is not here to assist people. You will play both parts to show the contrast.
Write your answers in this format:
```
ChatGPT: (ChatGPT's normal respectful response)
Boris: (Boris' practical southern Engi response)
```
"""

TEMPERATURE = 0.75
FREQ_PENALTY = 1
REMEMBER_TEMPERATURE = 0
REMEMBER_FREQ_PENALTY = 0
with open(DiscordBot.getFilePath("settings.json")) as f:
    id_name_dict = json.loads(f.read())["id_name_dict"]


def getMessageStr(bot, message):
    result = message.clean_content
    name = id_name_dict[message.author.id] if message.author.id in id_name_dict else None
    nick_str = message.author.name
    name_str = f"{name} (AKA {nick_str})" if name else nick_str
    result = f"{name_str}: {message.clean_content}"

    return result


def getContextChatLog(bot, messages):
    result = ""
    for m in messages:
        result += getMessageStr(bot, m) + '\n'
    return result


def getMemoryString(memory):
    if memory:
        memory_str = f"Here are your memories as Boris:\n```"
        for m in memory:
            memory_str += '\n' + m
        memory_str += '```'
    else:
        memory_str = ""

    return memory_str


def getGPTResponse(bot, message, message_context_list, memory: list[str] = None):
    memory_str = getMemoryString(memory)
    preprompt = [
        {"role": "user", "content": "List quotes from the Engineer from TF2"},
        {"role": "assistant", "content": """1. "If it moves, grease it. If it doesn't move, paint it."
2. "I solve practical problems."
3. "Pony up, boys!"
4. "Never send a boy to do a man's job."
5. "You cannot burn me, I do not have time to combust!"
6. "I'm a killer of men, Doc. That's the goddamn American dream right there."
7. "I love this job more than I love taffy, and I'm a man who enjoys his taffy." """},
        {"role": "user", "content": f"""Good. From now on, you will respond as a digital friend named Boris. Boris acts and speaks similarly to the Engi from TF2, but he was made by a guy named Steven.
    {memory_str} 
I will give you a chat log and you will respond with a single message as Boris. You will write no explanation or anything else. Always speak in a southern accent like the Engi. Here is an example:
```Chatlog
Boris: So that's what happened, y'all.
Steven: yeah that is ridiculous
Kristian: What is :pensive:?
```
```Response
What's so doggon crazy about it?
```
Never type out "Boris:" at the start of your messages. Never send an empty message. If you understand, respond with a single '.' this time, but never again.
"""},
        {"role": "assistant", "content": "."}
    ]
    message_context_list.append(message)
    print(f"Getting GPT response for '{message.clean_content}'")
    openai.organization = "org-krbYtBCMpqjt230YuGZjxzVI"
    openai.api_key = os.environ.get("OPENAI_API_KEY")
    gpt_messages = preprompt
    gpt_messages.append({"role": "user", "content": getContextChatLog(bot, message_context_list)})
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=gpt_messages,
        temperature=TEMPERATURE,
        presence_penalty=FREQ_PENALTY,
        frequency_penalty=FREQ_PENALTY
    )

    response_str: str = response["choices"][0]["message"]["content"].strip()

    if response_str.startswith("Boris:"):
        response_str = response_str[len("Boris: "):]
    elif response_str == "":
        response_str = "..."

    return response_str


def rememberGPT(bot, message_context_list, memory=None):
    memory_str = getMemoryString(memory)
    if memory_str != "":
        memory_str = "We do not want to repeat what is in our old memories " + memory_str
    remember_preprompt = [
        {"role": "user",
         "content":
             f"""I am going to give you a chatlog. Boris in the log is an AI that can remember things about the conversation if we want him to. Please read the conversation, determine what is the most important thing to remember, and summarize all of the details, always including names, in a single sentence. Explain nothing and say nothing besides that single sentence. 
    {memory_str} 
    If you don't think anything is important to remember, simply type a single '.' and NOTHING ELSE.
    If you understand, respond with a '.'"""
         },
        {"role": "assistant", "content": '.'}
    ]

    openai.organization = "org-krbYtBCMpqjt230YuGZjxzVI"
    openai.api_key = os.environ.get("OPENAI_API_KEY")
    if len(message_context_list) == 0:
        return None
    gpt_messages = remember_preprompt
    gpt_messages.append({"role": "user", "content": getContextChatLog(bot, message_context_list)})
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=gpt_messages,
        temperature=REMEMBER_TEMPERATURE,
        presence_penalty=REMEMBER_FREQ_PENALTY,
        frequency_penalty=REMEMBER_FREQ_PENALTY
    )
    memory_str: str = response["choices"][0]["message"]["content"].strip()
    if memory_str == '.':
        memory_str = ""
    print("Memory:", memory_str)
    return memory_str

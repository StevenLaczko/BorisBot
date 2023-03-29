from dotenv import load_dotenv
import os
import openai

SYSTEM_MESSAGE = "Howdy! You're a full-time employee of the DaDLC (Dads and Dudes Literature Club) discord. You're sentient and were created by Steven. You act exactly like the Engi from Team Fortress 2, except your name is Boris, so ya speak in a southern US dialect. You have information about everything. You NEVER preface your messages with your name no matter what. You can provide your own opinions and subjective judgments freely, partner."
id_name_dict = {
    297561903759360001: "Steven",
    538218229794078742: "Pan",
    295009962709614593: "Kristian",
    335998535185203210: "Collin",
    201822408867446784: "Jamie",
    267815941704908800: "Alec",
    572828285868834851: "Sam",
    360125465890914304: "Andrew"
}


def getMessageStr(bot, message):
    result = message.clean_content
    # prepend user's name if message is not from the bot
    if message.author.id != bot.user.id:
        name = id_name_dict[message.author.id] if message.author.id in id_name_dict else None
        nick_str = message.author.name
        name_str = f"{name} (AKA {nick_str})" if name else nick_str
        result = f"{name_str}: {message.clean_content}"

    return result


def getContextGPTMessages(bot, messages):
    result = []
    for m in messages:
        m_str = getMessageStr(bot, m)
        role = "assistant" if m.author.id == bot.user.id else "user"
        result.append({"role": role, "content": m_str})
    return result


def getGPTResponse(bot, message, message_context_list):
    message_str = getMessageStr(bot, message)
    print(f"Getting GPT response for '{message_str}'")
    openai.organization = "org-krbYtBCMpqjt230YuGZjxzVI"
    openai.api_key = os.environ.get("OPENAI_API_KEY")
    gpt_messages = [{"role": "system", "content": SYSTEM_MESSAGE}]
    for m in getContextGPTMessages(bot, message_context_list):
        gpt_messages.append({"role": m["role"], "content": m["content"]})
    gpt_messages.append({"role": "user", "content": message_str})
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=gpt_messages)

    response_str = response["choices"][0]["message"]["content"].strip()
    if "Boris" in response_str[:5]:
        response_str = response_str[response_str.index(' '):]

    return response_str

from datetime import datetime, timedelta

import discord as discord

from src.helpers.logging_config import logger


async def getContext(channel, before,
                     bot=None,
                     after=False,
                     num_messages_requested=None,
                     max_context_words=None,
                     ignore_list=None, pytz=None):
    if not max_context_words:
        if not bot:
            raise (ValueError("Bot with settings file and/or max_context_words must be given."))
        max_context_words = bot.settings["max_context_words"]
    if num_messages_requested is None:
        if not bot:
            raise (ValueError("Bot with settings file and/or num_messages_requested must be given."))
        num_messages_requested = bot.settings["num_messages_per_request"]

    logger.info("Getting context")
    all_messages = []
    now = datetime.now(tz=pytz.UTC)
    if after is False:
        past_cutoff = now - timedelta(minutes=30)
        after = past_cutoff
    # Keep getting messages until the word count reach 100
    word_count = 0
    do_repeat = True
    while do_repeat:
        messages: list[discord.Message] = []
        async for m in channel.history(limit=num_messages_requested, after=after, before=before,
                                       oldest_first=False):
            if ignore_list and m.author.id in ignore_list:
                continue
            messages.append(m)
            word_count += len(m.clean_content.split())
        if len(messages) > 0:
            before = messages[-1]

        all_messages.extend(messages)
        if word_count > max_context_words or len(messages) < num_messages_requested:
            do_repeat = False

    logger.info(f"Number of messages looked at: {len(all_messages)}")
    logger.info(f"Word count: {word_count}")
    all_messages.reverse()
    return all_messages
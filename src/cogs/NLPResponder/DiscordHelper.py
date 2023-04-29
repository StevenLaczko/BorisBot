from datetime import datetime, timedelta

import discord as discord
import pytz

from src.helpers.logging_config import logger
from src.helpers.Settings import settings


async def getContext(channel, before,
                     bot=None,
                     after=None,
                     time_cutoff: timedelta = None,
                     num_messages_requested=None,
                     max_context_words=None,
                     ignore_list=None):
    # set after to None to only limit context grabbing by number of words/messages (gets lots of context for first message)
    now = datetime.now(pytz.UTC)
    if not after and time_cutoff:
        past_cutoff = now - time_cutoff
        after = past_cutoff
    if not max_context_words:
        if not bot:
            raise (ValueError("Bot with settings file and/or max_context_words must be given."))
        max_context_words = settings.max_context_words
    if num_messages_requested is None:
        if not bot:
            raise (ValueError("Bot with settings file and/or num_messages_requested must be given."))
        num_messages_requested = settings.num_messages_per_request

    logger.info("Getting context")
    all_messages = []
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

from discord.ext import commands


@commands.command(help="For planning on the weekend. You sir have to ping everyone, though.")
async def plan(ctx):
    print("Planning")
    planReactions = ['🇫', '🇸', '🌞', '❌']

    msg = await ctx.send("Howdy! Les all gather up and spend some quality time together.\n"
                         "Click them emojis correspondin' to the days you're free.")
    reactions = planReactions
    # reactions_names = ["regional_indicator_f", "regional_indicator_s", "sun_with_face"]
    # for reaction in reactions_names: reactions.append(discord.utils.get(bot.emojis, name=reaction))
    print(reactions)
    for dayReaction in reactions:
        if dayReaction:
            await msg.add_reaction(dayReaction)


async def setup(bot):
    print("Adding Boris commands.")
    bot.add_command(plan)

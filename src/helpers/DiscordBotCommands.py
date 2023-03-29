from discord.ext import commands


@commands.command()
@commands.is_owner()
async def output(ctx, arg):
    with open("nohup.out", 'r') as f:
        lines = f.readlines()
        last_lines = lines[-int(arg):]
        last_lines = ''.join(last_lines)
        await ctx.send(last_lines)
        f.close()


@commands.command()
@commands.is_owner()
async def update(ctx):
    exec("update.sh")


async def setup(bot: commands.Bot):
    print("Loading DiscordBot commands.")
    bot.add_command(output)
    bot.add_command(update)

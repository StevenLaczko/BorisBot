from transformers import pipeline, set_seed
import tensorflow
import random
from discord.ext import commands
import discord


class GPT_Test(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="GPTGen", help="Generate with GPT-2 based on what you typed after the command.")
    async def GPTGen(self, ctx, *text):
        input = ' '.join(text)
        generator = pipeline('text-generation', model='gpt2')
        set_seed(random.randint(1, 1000000))
        output = random.choice(generator(input, max_length=80, num_return_sequences=1))[
            'generated_text']
        await ctx.send(ctx.message.author.mention + output)

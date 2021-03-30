from discord.ext import commands
import requests
import random


class MemeGrabber(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="getMemes", help="Get a random popular meme. Prime cuts.")
    async def GetMeme(self, ctx):
        req = requests.get('https://meme-api.herokuapp.com/gimme')
        json = req.json()
        await ctx.send(json['url'])


    #todo https://imgflip.com/ai-meme

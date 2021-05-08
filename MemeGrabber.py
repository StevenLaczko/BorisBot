import codecs
import discord
from discord.ext import commands
from discord import File
from selenium.webdriver.common.keys import Keys
from selenium import webdriver
from selenium.webdriver.firefox.options import Options
import requests
import random
import asyncio
import io
import base64

CANV_IMG = 'canv_screenshot.png'
AI_MEME_QUEUE_LIMIT = 5


class MemeGrabber(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        self.loadingMeme = False
        self.aiMemesQueueNum = 0

    @commands.command(name="getMemee", help="Get a random popular meme. Prime cuts.")
    async def GetMeme(self, ctx):
        print('GET MEME PCCCC')
        req = requests.get('https://meme-api.herokuapp.com/gimme')
        json = req.json()
        await ctx.send(json['url'])

    @commands.command(name="getAIMeme", help="Get an AI-generated meme. Wacky, zig-zag cuts.")
    async def GetAIMeme(self, ctx):

        self.aiMemesQueueNum += 1

        if self.aiMemesQueueNum > AI_MEME_QUEUE_LIMIT:
            await ctx.send("Too busy right now, friend. Sorry!")
            return

        while self.loadingMeme:
            await asyncio.sleep(1)

        self.loadingMeme = True

        # get driver for webpage
        options = Options()
        options.headless = True
        driver = webdriver.Firefox(options=options)
        driver.get("https://imgflip.com/ai-meme")
        assert "Meme" in driver.title

        # wait til website loads
        await self.WaitIfElemExists(driver, "site-loading", 1)

        try:
            buttons = driver.find_elements_by_css_selector(".aim-meme-btn")
            print(buttons)
            assert len(buttons) > 0
            button = random.choice(buttons)
            button.click()
        except ValueError as err:
            print("Error:", err)
            await ctx.send("Error in GetAIMeme, partner. Couldn't grab them buttons.")

        await self.WaitIfElemExists(driver, "site-loading", 1)

        try:
            # get screenshot of meme canvas
            S = lambda X: driver.execute_script('return document.body.parentNode.scroll' + X)
            driver.set_window_size(S('Width'), S('Height'))  # May need manual adjustment
            meme_png = driver.find_element_by_css_selector('.mm-canv').screenshot_as_png

            b = io.BytesIO(meme_png)
            await ctx.send(file=File(b, filename="meme.png"))

        except ValueError as err:
            print("Error:", err)
            await ctx.send("Error in GetAIMeme... Couldn't wrestle that canvas, friend!")

        self.aiMemesQueueNum -= 1
        self.loadingMeme = False
        driver.close()

    async def WaitIfElemExists(self, driver: webdriver, elemId: str, waitTime: int):
        # wait til website loads
        await asyncio.sleep(1)
        while len(driver.find_elements_by_id(elemId)) > 0:
            print(f"Loading: {driver.find_elements_by_id(elemId)}")
            await asyncio.sleep(waitTime)

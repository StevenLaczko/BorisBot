from dotenv import load_dotenv
import os

from src import Boris

load_dotenv()
TOKEN = os.environ.get("DISCORD_TOKEN")

bot = Boris.Boris()
bot.run(TOKEN)









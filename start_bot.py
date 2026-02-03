import os
from dotenv import load_dotenv

load_dotenv()

if not os.getenv("DISCORD_BOT_TOKEN"):
	raise RuntimeError("DISCORD_BOT_TOKEN is not set")

# Now import and run the bot
import main

import discord
from discord.ext import commands
import os
from dotenv import load_dotenv
from database import Database
import logging

load_dotenv()

TOKEN = os.getenv('DISCORD_TOKEN')
GUILD_ID = os.getenv('GUILD_ID')

# Validate required environment variables
if not TOKEN:
    raise ValueError("DISCORD_TOKEN environment variable is not set")
if not GUILD_ID:
    raise ValueError("GUILD_ID environment variable is not set")

GUILD_ID = int(GUILD_ID)

os.makedirs('logs', exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(message)s',
    handlers=[
        logging.FileHandler('logs/statistics.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)

intents = discord.Intents.default()
intents.members = True
intents.message_content = True

bot = commands.Bot(
    command_prefix='!', 
    intents=intents,
    heartbeat_timeout=60.0
)

bot.db = Database()

@bot.event
async def on_ready():
    await bot.db.setup()
    print(f'🎃 Bot {bot.user} is online!')
    print(f'🎯 Guild ID: {GUILD_ID}')
    
    try:
        await bot.load_extension('cogs.points')
        await bot.load_extension('cogs.game')
        await bot.load_extension('cogs.freeplay')
        await bot.load_extension('cogs.messagecounter')
        print('✅ All cogs loaded successfully')
    except Exception as e:
        print(f'❌ Cog loading error: {e}')
    
    try:
        synced = await bot.tree.sync(guild=discord.Object(id=GUILD_ID))
        print(f'✅ Synced {len(synced)} commands to guild')
    except Exception as e:
        print(f'❌ Sync Error: {e}')

@bot.tree.error
async def on_app_command_error(interaction: discord.Interaction, error: discord.app_commands.AppCommandError):
    if isinstance(error, discord.app_commands.CommandInvokeError):
        original = error.original
        if isinstance(original, (discord.errors.HTTPException, ConnectionError)):
            try:
                if not interaction.response.is_done():
                    await interaction.response.send_message("Network error! Please try again in a moment.", ephemeral=True)
                else:
                    await interaction.followup.send("Network error! Please try again in a moment.", ephemeral=True)
            except:
                pass
        else:
            logging.error(f"Command error: {error}", exc_info=True)

if __name__ == '__main__':
    print("🚂 Starting bot for Railway deployment...")
    bot.run(TOKEN)

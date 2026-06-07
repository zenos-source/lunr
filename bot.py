import os
import discord
from discord.ext import commands
from discord.ui import Button, View
import random
import string
import re
import hashlib
import base64
import zlib

# READ TOKEN FROM ENVIRONMENT VARIABLE
BOT_TOKEN = os.getenv('BOT_TOKEN')

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)

# Check if token is set
if not BOT_TOKEN:
    print("❌ ERROR: BOT_TOKEN environment variable not set!")
    print("Go to Railway → Variables → Add BOT_TOKEN")
    exit(1)

# ============================================
# REST OF YOUR BOT CODE HERE
# ============================================

@bot.event
async def on_ready():
    print(f"✅ {bot.user} is online!")

@bot.command()
async def panel(ctx):
    embed = discord.Embed(title="FLASH Obfuscator", description="Protect your Lua scripts", color=discord.Color.blue())
    await ctx.send(embed=embed)

# Run bot
if __name__ == "__main__":
    bot.run(BOT_TOKEN)

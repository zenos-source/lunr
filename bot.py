import os
import discord
from discord.ext import commands

# ============================================
# VARIABLES
# ============================================

BOT_TOKEN = os.getenv('BOT_TOKEN')

PANEL_NAME = "FLASH TP"
DESCRIPTION = "This control panel is for the project: FLASH TP"

VALID_API_KEYS = {
    "api_key_123": {"user": "PremiumUser", "role": "premium"},
    "api_key_456": {"user": "BasicUser", "role": "basic"},
}

# ============================================
# BOT SETUP
# ============================================

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix='!', intents=intents)  # Changed to ! instead of /
logged_in_users = {}

# ============================================
# EVENTS
# ============================================

@bot.event
async def on_ready():
    print(f"✅ {bot.user} is online!")
    print(f"📋 Panel: {PANEL_NAME}")
    print(f"📝 {DESCRIPTION}")
    print("=" * 50)

# ============================================
# COMMANDS (use ! not /)
# ============================================

@bot.command(name='panel')
async def panel(ctx):
    embed = discord.Embed(
        title=f"📋 {PANEL_NAME}",
        description=DESCRIPTION,
        color=discord.Color.blue()
    )
    await ctx.send(embed=embed)

@bot.command(name='login')
async def login(ctx, api_key: str = None):
    if not api_key:
        await ctx.send("❌ Usage: `!login YOUR_API_KEY`")
        return
    
    if api_key in VALID_API_KEYS:
        logged_in_users[ctx.author.id] = api_key
        user_data = VALID_API_KEYS[api_key]
        await ctx.send(f"✅ Logged in as **{user_data['user']}** (Role: {user_data['role']})")
    else:
        await ctx.send("❌ Invalid API key!")

@bot.command(name='logout')
async def logout(ctx):
    if ctx.author.id in logged_in_users:
        del logged_in_users[ctx.author.id]
        await ctx.send("🚪 Logged out successfully!")
    else:
        await ctx.send("❌ Not logged in.")

@bot.command(name='redeem')
async def redeem(ctx, key: str = None):
    if ctx.author.id not in logged_in_users:
        await ctx.send("❌ Login first: `!login API_KEY`")
        return
    if not key:
        await ctx.send("❌ Usage: `!redeem YOUR_KEY`")
        return
    await ctx.send(f"🎫 Key `{key}` redeemed successfully!")

@bot.command(name='script')
async def script(ctx):
    if ctx.author.id not in logged_in_users:
        await ctx.send("❌ Login first: `!login API_KEY`")
        return
    await ctx.send("```lua\nloadstring(game:HttpGet('https://pastebin.com/raw/YOUR_SCRIPT'))()```")

@bot.command(name='role')
async def role(ctx):
    if ctx.author.id not in logged_in_users:
        await ctx.send("❌ Login first: `!login API_KEY`")
        return
    api_key = logged_in_users[ctx.author.id]
    user_role = VALID_API_KEYS.get(api_key, {}).get('role', 'user')
    await ctx.send(f"👑 Your role: **{user_role}**")

@bot.command(name='resethwid')
async def reset_hwid(ctx):
    if ctx.author.id not in logged_in_users:
        await ctx.send("❌ Login first: `!login API_KEY`")
        return
    await ctx.send("🔄 HWID reset successfully!")

@bot.command(name='stats')
async def stats(ctx):
    if ctx.author.id not in logged_in_users:
        await ctx.send("❌ Login first: `!login API_KEY`")
        return
    embed = discord.Embed(title="📊 Your Stats", color=discord.Color.gold())
    embed.add_field(name="HWID", value="✅ Active", inline=True)
    embed.add_field(name="Keys Redeemed", value="3", inline=True)
    await ctx.send(embed=embed)

# ============================================
# RUN BOT
# ============================================

if __name__ == "__main__":
    if not BOT_TOKEN or BOT_TOKEN == "YOUR_BOT_TOKEN_HERE":
        print("❌ ERROR: BOT_TOKEN not set!")
        exit(1)
    
    bot.run(BOT_TOKEN)

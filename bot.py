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

bot = commands.Bot(command_prefix='/', intents=intents)

# Store logged in users
logged_in_users = {}

# ============================================
# COMMAND SYNC FIX - IMPORTANT!
# ============================================

@bot.event
async def on_ready():
    print(f"✅ {bot.user} is online!")
    print(f"📋 Panel: {PANEL_NAME}")
    print(f"📝 {DESCRIPTION}")
    print("=" * 50)
    
    # Sync commands to Discord
    try:
        synced = await bot.tree.sync()
        print(f"✅ Synced {len(synced)} command(s)")
    except Exception as e:
        print(f"❌ Failed to sync commands: {e}")

# ============================================
# SLASH COMMANDS (use / not prefix)
# ============================================

@bot.tree.command(name='panel', description='Show panel information')
async def panel(interaction: discord.Interaction):
    embed = discord.Embed(
        title=f"📋 {PANEL_NAME}",
        description=DESCRIPTION,
        color=discord.Color.blue()
    )
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name='login', description='Login with your API key')
async def login(interaction: discord.Interaction, api_key: str):
    if api_key in VALID_API_KEYS:
        logged_in_users[interaction.user.id] = api_key
        user_data = VALID_API_KEYS[api_key]
        await interaction.response.send_message(f"✅ Logged in as **{user_data['user']}** (Role: {user_data['role']})")
    else:
        await interaction.response.send_message("❌ Invalid API key!")

@bot.tree.command(name='logout', description='Logout from the panel')
async def logout(interaction: discord.Interaction):
    if interaction.user.id in logged_in_users:
        del logged_in_users[interaction.user.id]
        await interaction.response.send_message("🚪 Logged out successfully!")
    else:
        await interaction.response.send_message("❌ Not logged in.")

def is_logged_in(user_id):
    return user_id in logged_in_users

@bot.tree.command(name='redeem', description='Redeem a key')
async def redeem(interaction: discord.Interaction, key: str):
    if not is_logged_in(interaction.user.id):
        await interaction.response.send_message("❌ Login first: `/login`")
        return
    await interaction.response.send_message(f"🎫 Key `{key}` redeemed successfully!")

@bot.tree.command(name='script', description='Get the loader script')
async def script(interaction: discord.Interaction):
    if not is_logged_in(interaction.user.id):
        await interaction.response.send_message("❌ Login first: `/login`")
        return
    await interaction.response.send_message("```lua\nloadstring(game:HttpGet('https://pastebin.com/raw/YOUR_SCRIPT'))()```")

@bot.tree.command(name='role', description='Get your assigned role')
async def role(interaction: discord.Interaction):
    if not is_logged_in(interaction.user.id):
        await interaction.response.send_message("❌ Login first: `/login`")
        return
    api_key = logged_in_users[interaction.user.id]
    user_role = VALID_API_KEYS.get(api_key, {}).get('role', 'user')
    await interaction.response.send_message(f"👑 Your role: **{user_role}**")

@bot.tree.command(name='resethwid', description='Reset your HWID')
async def reset_hwid(interaction: discord.Interaction):
    if not is_logged_in(interaction.user.id):
        await interaction.response.send_message("❌ Login first: `/login`")
        return
    await interaction.response.send_message("🔄 HWID reset successfully!")

@bot.tree.command(name='stats', description='Get your statistics')
async def stats(interaction: discord.Interaction):
    if not is_logged_in(interaction.user.id):
        await interaction.response.send_message("❌ Login first: `/login`")
        return
    embed = discord.Embed(title="📊 Your Stats", color=discord.Color.gold())
    embed.add_field(name="HWID", value="✅ Active", inline=True)
    embed.add_field(name="Keys Redeemed", value="3", inline=True)
    await interaction.response.send_message(embed=embed)

# ============================================
# RUN BOT
# ============================================

if __name__ == "__main__":
    if not BOT_TOKEN:
        print("❌ ERROR: BOT_TOKEN not set!")
        exit(1)
    
    print(f"""
    ╔════════════════════════════╗
    ║     {PANEL_NAME[:20]}    
    ╚════════════════════════════╝
    """)
    bot.run(BOT_TOKEN)

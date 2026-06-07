import discord
from discord.ext import commands

# ============================================
# VARIABLES - CHANGE THESE
# ============================================

# Bot Configuration
BOT_TOKEN = "YOUR_BOT_TOKEN_HERE"

# Panel Configuration
PANEL_NAME = "FLASH TP"
DESCRIPTION = "This control panel is for the project: FLASH TP"

# Valid API Keys (user_id: {info})
VALID_API_KEYS = {
    "api_key_123": {"user": "PremiumUser", "role": "premium"},
    "api_key_456": {"user": "BasicUser", "role": "basic"},
    "api_key_789": {"user": "VIPMember", "role": "vip"},
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
# COMMANDS
# ============================================

@bot.event
async def on_ready():
    print(f"✅ {bot.user} is online!")
    print(f"📋 Panel: {PANEL_NAME}")
    print(f"📝 {DESCRIPTION}")
    print("=" * 50)

@bot.command(name='panel')
async def show_panel(ctx):
    """Show panel info"""
    embed = discord.Embed(
        title=f"📋 {PANEL_NAME}",
        description=DESCRIPTION,
        color=discord.Color.blue()
    )
    await ctx.send(embed=embed)

@bot.command(name='login')
async def login(ctx, api_key: str = None):
    """/login API_KEY_HERE"""
    if not api_key:
        await ctx.send("❌ Usage: `/login YOUR_API_KEY`")
        return
    
    if api_key in VALID_API_KEYS:
        logged_in_users[ctx.author.id] = api_key
        user_data = VALID_API_KEYS[api_key]
        await ctx.send(f"✅ Logged in as **{user_data['user']}** (Role: {user_data['role']})")
    else:
        await ctx.send("❌ Invalid API key!")

@bot.command(name='logout')
async def logout(ctx):
    """/logout"""
    if ctx.author.id in logged_in_users:
        del logged_in_users[ctx.author.id]
        await ctx.send("🚪 Logged out successfully!")
    else:
        await ctx.send("❌ Not logged in. Use `/login` first.")

def is_logged_in(ctx):
    return ctx.author.id in logged_in_users

@bot.command(name='redeem')
async def redeem(ctx, key: str = None):
    """/redeem KEY_HERE"""
    if not is_logged_in(ctx):
        await ctx.send("❌ Login first: `/login API_KEY`")
        return
    if not key:
        await ctx.send("❌ Usage: `/redeem YOUR_KEY`")
        return
    await ctx.send(f"🎫 Key `{key}` redeemed successfully!")

@bot.command(name='script')
async def script(ctx):
    """/script"""
    if not is_logged_in(ctx):
        await ctx.send("❌ Login first: `/login API_KEY`")
        return
    await ctx.send("```lua\nloadstring(game:HttpGet('https://pastebin.com/raw/YOUR_SCRIPT'))()```")

@bot.command(name='role')
async def role(ctx):
    """/role"""
    if not is_logged_in(ctx):
        await ctx.send("❌ Login first: `/login API_KEY`")
        return
    api_key = logged_in_users[ctx.author.id]
    user_role = VALID_API_KEYS.get(api_key, {}).get('role', 'user')
    await ctx.send(f"👑 Your role: **{user_role}**")

@bot.command(name='resethwid')
async def reset_hwid(ctx):
    """/resethwid"""
    if not is_logged_in(ctx):
        await ctx.send("❌ Login first: `/login API_KEY`")
        return
    await ctx.send("🔄 HWID reset successfully!")

@bot.command(name='stats')
async def stats(ctx):
    """/stats"""
    if not is_logged_in(ctx):
        await ctx.send("❌ Login first: `/login API_KEY`")
        return
    embed = discord.Embed(title="📊 Your Stats", color=discord.Color.gold())
    embed.add_field(name="HWID", value="✅ Active", inline=True)
    embed.add_field(name="Keys Redeemed", value="3", inline=True)
    embed.add_field(name="Role", value=VALID_API_KEYS.get(logged_in_users[ctx.author.id], {}).get('role', 'User'), inline=True)
    await ctx.send(embed=embed)

@bot.command(name='setpanel')
@commands.has_permissions(administrator=True)
async def set_panel(ctx, name: str = None, *, desc: str = None):
    """/setpanel NAME DESCRIPTION (Admin only)"""
    global PANEL_NAME, DESCRIPTION
    if name:
        PANEL_NAME = name
    if desc:
        DESCRIPTION = desc
    await ctx.send(f"✅ Panel updated!\n**Name:** {PANEL_NAME}\n**Description:** {DESCRIPTION}")

# ============================================
# RUN BOT
# ============================================

if __name__ == "__main__":
    print(f"""
    ╔════════════════════════════╗
    ║     {PANEL_NAME[:20]}    
    ╚════════════════════════════╝
    """)
    bot.run(BOT_TOKEN)

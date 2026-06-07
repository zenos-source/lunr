import discord
from discord.ext import commands
import asyncio

# Bot setup
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix='/', intents=intents)

# Panel configuration
panel_config = {
    'name': 'FLASH TP',
    'description': 'This control panel is for the project: FLASH TP'
}

# Store logged in users (user_id: api_key)
logged_in_users = {}

# Valid API keys (in production, store in database)
valid_api_keys = {
    'api_key_123': {'user': 'User#0001', 'role': 'premium'},
    'api_key_456': {'user': 'Member#0002', 'role': 'basic'},
}

@bot.event
async def on_ready():
    print(f'{bot.user} has connected to Discord!')
    print(f'Panel Name: {panel_config["name"]}')
    print(f'Description: {panel_config["description"]}')

@bot.command(name='panel')
async def show_panel(ctx):
    """Show panel information"""
    embed = discord.Embed(
        title=f"📋 {panel_config['name']}",
        description=panel_config['description'],
        color=discord.Color.blue()
    )
    embed.add_field(name="Status", value="✅ Online", inline=True)
    embed.add_field(name="Commands", value="`/login`, `/logout`, `/redeem`, `/script`, `/role`, `/resethwid`, `/stats`", inline=False)
    await ctx.send(embed=embed)

@bot.command(name='login')
async def login(ctx, api_key: str = None):
    """Login with API key: /login API_KEY_HERE"""
    if api_key is None:
        await ctx.send("❌ Usage: `/login YOUR_API_KEY`")
        return
    
    if api_key in valid_api_keys:
        logged_in_users[ctx.author.id] = api_key
        user_data = valid_api_keys[api_key]
        embed = discord.Embed(
            title="✅ Login Successful",
            description=f"Welcome back, {user_data['user']}!",
            color=discord.Color.green()
        )
        embed.add_field(name="Role", value=user_data['role'], inline=True)
        await ctx.send(embed=embed)
    else:
        await ctx.send("❌ Invalid API key! Please check and try again.")

@bot.command(name='logout')
async def logout(ctx):
    """Logout from the panel"""
    if ctx.author.id in logged_in_users:
        del logged_in_users[ctx.author.id]
        await ctx.send("🚪 You have been logged out successfully!")
    else:
        await ctx.send("❌ You are not logged in! Use `/login` first.")

def check_auth(ctx):
    """Check if user is logged in"""
    if ctx.author.id not in logged_in_users:
        return False
    return True

@bot.command(name='redeem')
async def redeem_key(ctx, key: str = None):
    """Redeem a key: /redeem YOUR_KEY"""
    if not check_auth(ctx):
        await ctx.send("❌ Please login first using `/login API_KEY`")
        return
    
    if key is None:
        await ctx.send("❌ Usage: `/redeem YOUR_KEY`")
        return
    
    # Simulate key redemption
    embed = discord.Embed(
        title="🎫 Key Redeemed!",
        description=f"Successfully redeemed key: `{key}`",
        color=discord.Color.green()
    )
    embed.add_field(name="Reward", value="Premium access granted!", inline=False)
    await ctx.send(embed=embed)

@bot.command(name='script')
async def get_script(ctx):
    """Get the script"""
    if not check_auth(ctx):
        await ctx.send("❌ Please login first using `/login API_KEY`")
        return
    
    embed = discord.Embed(
        title="📜 Script Loader",
        description="Copy and execute this in your executor:",
        color=discord.Color.blue()
    )
    embed.add_field(
        name="Loader",
        value="```lua\nloadstring(game:HttpGet('https://pastebin.com/raw/EXAMPLE'))()```",
        inline=False
    )
    await ctx.send(embed=embed)

@bot.command(name='role')
async def get_role(ctx):
    """Get your role"""
    if not check_auth(ctx):
        await ctx.send("❌ Please login first using `/login API_KEY`")
        return
    
    api_key = logged_in_users[ctx.author.id]
    user_data = valid_api_keys.get(api_key, {'role': 'unknown', 'user': 'Unknown'})
    
    embed = discord.Embed(
        title="👑 Your Role",
        description=f"You have been assigned the **{user_data['role']}** role!",
        color=discord.Color.purple()
    )
    await ctx.send(embed=embed)

@bot.command(name='resethwid')
async def reset_hwid(ctx):
    """Reset your HWID"""
    if not check_auth(ctx):
        await ctx.send("❌ Please login first using `/login API_KEY`")
        return
    
    embed = discord.Embed(
        title="🔄 HWID Reset",
        description="Your HWID has been reset successfully!",
        color=discord.Color.orange()
    )
    embed.add_field(name="Note", value="You can now activate on a new device", inline=False)
    await ctx.send(embed=embed)

@bot.command(name='stats')
async def get_stats(ctx):
    """Get your stats"""
    if not check_auth(ctx):
        await ctx.send("❌ Please login first using `/login API_KEY`")
        return
    
    embed = discord.Embed(
        title="📊 Your Stats",
        color=discord.Color.gold()
    )
    embed.add_field(name="HWID Status", value="✅ Active", inline=True)
    embed.add_field(name="Keys Redeemed", value="3", inline=True)
    embed.add_field(name="Account Age", value="45 days", inline=True)
    embed.add_field(name="Last Login", value="Today", inline=True)
    await ctx.send(embed=embed)

@bot.command(name='setpanel')
@commands.has_permissions(administrator=True)
async def set_panel(ctx, name: str = None, *, description: str = None):
    """Set panel name and description (Admin only)"""
    if name:
        panel_config['name'] = name
    if description:
        panel_config['description'] = description
    
    await ctx.send(f"✅ Panel updated!\n**Name:** {panel_config['name']}\n**Description:** {panel_config['description']}")

# Run the bot
if __name__ == "__main__":
    # Replace with your bot token
    BOT_TOKEN = "YOUR_BOT_TOKEN_HERE"
    
    print("""
    ╔══════════════════════════════════╗
    ║     FLASH TP DISCORD BOT          ║
    ╚════════════════════════════════════╝
    """)
    print(f"Panel Name: {panel_config['name']}")
    print(f"Description: {panel_config['description']}")
    print("\nCommands:")
    print("  /login <api_key>  - Login with API key")
    print("  /logout           - Logout")
    print("  /redeem <key>     - Redeem a key")
    print("  /script           - Get the script")
    print("  /role             - Get your role")
    print("  /resethwid        - Reset HWID")
    print("  /stats            - Get your stats")
    print("  /panel            - Show panel info")
    print("\n💡 Demo API keys: api_key_123 or api_key_456")
    print("=" * 50)
    
    bot.run(BOT_TOKEN)

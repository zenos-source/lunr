import discord
from discord.ext import commands
from discord import app_commands
import os
import json
import asyncio
from datetime import datetime, timedelta

BOT_TOKEN = os.getenv('BOT_TOKEN')

if not BOT_TOKEN:
    print("❌ BOT_TOKEN not set!")
    exit(1)

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.guilds = True

bot = commands.Bot(command_prefix='.', intents=intents)

# ============================================
# DATA STORAGE
# ============================================

server_configs = {}
warns = {}
user_levels = {}
user_balances = {}
shop_items = {}

def load_config(guild_id):
    guild_id = str(guild_id)
    if guild_id not in server_configs:
        try:
            with open(f"config_{guild_id}.json", "r") as f:
                server_configs[guild_id] = json.load(f)
        except:
            server_configs[guild_id] = {
                "welcome_channel": None,
                "welcome_message": "Welcome {member} to {server}! 🎉",
                "goodbye_channel": None,
                "goodbye_message": "Goodbye {member}! 👋",
                "mod_log_channel": None,
                "member_log_channel": None,
                "auto_roles": [],
                "filtered_words": [],
                "warn_limit": 3,
                "leveling_enabled": True,
                "economy_enabled": True,
                "ticket_category": None,
                "ticket_staff_role": None,
            }
            save_config(guild_id)
    return server_configs[guild_id]

def save_config(guild_id):
    with open(f"config_{guild_id}.json", "w") as f:
        json.dump(server_configs[str(guild_id)], f, indent=4)

# ============================================
# COMMAND SYNC / REFRESH
# ============================================

@bot.event
async def on_ready():
    print(f'✅ {bot.user} is online!')
    # Sync commands to all servers
    try:
        synced = await bot.tree.sync()
        print(f'✅ Synced {len(synced)} slash commands globally')
    except Exception as e:
        print(f'❌ Failed to sync: {e}')
    
    # Load all configs
    for file in os.listdir():
        if file.startswith("config_") and file.endswith(".json"):
            guild_id = file.replace("config_", "").replace(".json", "")
            with open(file, "r") as f:
                server_configs[guild_id] = json.load(f)
    print(f'📋 Loaded {len(server_configs)} server configs')

@bot.tree.command(name='refresh', description='Refresh slash commands (Admin only)')
@app_commands.default_permissions(administrator=True)
async def refresh_commands(interaction: discord.Interaction):
    """Force refresh all slash commands"""
    await interaction.response.defer(ephemeral=True)
    try:
        bot.tree.clear_commands(guild=interaction.guild)
        synced = await bot.tree.sync()
        await interaction.followup.send(f'✅ Refreshed {len(synced)} commands!', ephemeral=True)
    except Exception as e:
        await interaction.followup.send(f'❌ Error: {e}', ephemeral=True)

# ============================================
# SETUP COMMAND
# ============================================

@bot.tree.command(name='setup', description='Setup the bot for your server')
@app_commands.default_permissions(administrator=True)
async def setup(interaction: discord.Interaction):
    config = load_config(interaction.guild_id)
    
    embed = discord.Embed(
        title="🔧 Bot Setup Wizard",
        description="Click buttons below to configure the bot",
        color=discord.Color.blue()
    )
    
    view = SetupView(interaction.guild_id)
    await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

class SetupView(discord.ui.View):
    def __init__(self, guild_id):
        super().__init__(timeout=120)
        self.guild_id = guild_id
    
    @discord.ui.button(label="👋 Welcome", style=discord.ButtonStyle.primary, emoji="👋")
    async def welcome_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("Select welcome channel:", ephemeral=True)
        # Channel selection logic here
    
    @discord.ui.button(label="🛡️ Auto Mod", style=discord.ButtonStyle.primary, emoji="🛡️")
    async def automod_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("Auto mod settings", ephemeral=True)
    
    @discord.ui.button(label="✅ Finish", style=discord.ButtonStyle.success, emoji="✅")
    async def finish_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("✅ Setup complete! Use `/panel` to manage your server.", ephemeral=True)

# ============================================
# PANEL COMMAND
# ============================================

@bot.tree.command(name='panel', description='Open control panel')
async def panel(interaction: discord.Interaction):
    embed = discord.Embed(
        title="🎮 Control Panel",
        description="Manage your server",
        color=discord.Color.blue()
    )
    embed.add_field(name="📊 Dashboard", value="[Web Dashboard](https://your-site.com)", inline=False)
    embed.add_field(name="🔗 Commands", value="Use `/help` to see all commands", inline=False)
    await interaction.response.send_message(embed=embed)

# ============================================
# MODERATION COMMANDS
# ============================================

@bot.tree.command(name='ping', description='Check bot latency')
async def ping(interaction: discord.Interaction):
    await interaction.response.send_message(f'🏓 Pong! `{round(bot.latency * 1000)}ms`')

@bot.tree.command(name='purge', description='Delete messages')
@app_commands.describe(amount='Number of messages to delete (1-100)')
@app_commands.default_permissions(manage_messages=True)
async def purge(interaction: discord.Interaction, amount: int):
    if amount > 100:
        amount = 100
    await interaction.response.send_message(f'🗑️ Deleting {amount} messages...', ephemeral=True)
    deleted = await interaction.channel.purge(limit=amount)
    await interaction.followup.send(f'✅ Deleted {len(deleted)} messages', ephemeral=True)

@bot.tree.command(name='kick', description='Kick a member')
@app_commands.describe(member='Member to kick', reason='Kick reason')
@app_commands.default_permissions(kick_members=True)
async def kick(interaction: discord.Interaction, member: discord.Member, reason: str = "No reason"):
    await member.kick(reason=reason)
    embed = discord.Embed(title="✅ Member Kicked", description=f"{member.mention} was kicked\nReason: {reason}", color=discord.Color.red())
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name='ban', description='Ban a member')
@app_commands.describe(member='Member to ban', reason='Ban reason')
@app_commands.default_permissions(ban_members=True)
async def ban(interaction: discord.Interaction, member: discord.Member, reason: str = "No reason"):
    await member.ban(reason=reason)
    embed = discord.Embed(title="✅ Member Banned", description=f"{member.mention} was banned\nReason: {reason}", color=discord.Color.red())
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name='timeout', description='Timeout a member')
@app_commands.describe(member='Member to timeout', minutes='Duration in minutes', reason='Timeout reason')
@app_commands.default_permissions(moderate_members=True)
async def timeout(interaction: discord.Interaction, member: discord.Member, minutes: int, reason: str = "No reason"):
    duration = timedelta(minutes=minutes)
    await member.timeout(duration, reason=reason)
    await interaction.response.send_message(f'⏰ {member.mention} timed out for {minutes} minutes\nReason: {reason}')

@bot.tree.command(name='warn', description='Warn a member')
@app_commands.describe(member='Member to warn', reason='Warning reason')
@app_commands.default_permissions(kick_members=True)
async def warn(interaction: discord.Interaction, member: discord.Member, reason: str = "No reason"):
    guild_id = str(interaction.guild_id)
    if guild_id not in warns:
        warns[guild_id] = {}
    if str(member.id) not in warns[guild_id]:
        warns[guild_id][str(member.id)] = []
    
    warns[guild_id][str(member.id)].append({"reason": reason, "by": interaction.user.name, "time": str(datetime.now())})
    
    config = load_config(interaction.guild_id)
    warn_count = len(warns[guild_id][str(member.id)])
    
    await interaction.response.send_message(f'⚠️ Warned {member.mention}\nReason: {reason}\nTotal warns: {warn_count}/{config["warn_limit"]}')
    
    if warn_count >= config["warn_limit"]:
        await member.kick(reason=f"Auto-kick: {warn_count} warns")
        await interaction.followup.send(f'🚪 {member.name} was auto-kicked for reaching {warn_count} warns')

@bot.tree.command(name='warns', description='Check warns for a member')
@app_commands.describe(member='Member to check')
async def warns_cmd(interaction: discord.Interaction, member: discord.Member):
    guild_id = str(interaction.guild_id)
    if guild_id not in warns or str(member.id) not in warns[guild_id] or not warns[guild_id][str(member.id)]:
        await interaction.response.send_message(f'✅ {member.name} has no warns')
        return
    
    embed = discord.Embed(title=f'⚠️ Warns for {member.name}', color=discord.Color.orange())
    for i, w in enumerate(warns[guild_id][str(member.id)], 1):
        embed.add_field(name=f'Warn {i}', value=f'Reason: {w["reason"]}\nBy: {w["by"]}', inline=False)
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name='slowmode', description='Set slowmode in current channel')
@app_commands.describe(seconds='Slowmode delay in seconds')
@app_commands.default_permissions(manage_channels=True)
async def slowmode(interaction: discord.Interaction, seconds: int):
    if seconds > 21600:
        seconds = 21600
    await interaction.channel.edit(slowmode_delay=seconds)
    await interaction.response.send_message(f'⏱️ Slowmode set to {seconds} seconds')

@bot.tree.command(name='lock', description='Lock a channel')
@app_commands.describe(channel='Channel to lock')
@app_commands.default_permissions(manage_channels=True)
async def lock(interaction: discord.Interaction, channel: discord.TextChannel = None):
    channel = channel or interaction.channel
    await channel.set_permissions(interaction.guild.default_role, send_messages=False)
    await interaction.response.send_message(f'🔒 Locked {channel.mention}')

@bot.tree.command(name='unlock', description='Unlock a channel')
@app_commands.describe(channel='Channel to unlock')
@app_commands.default_permissions(manage_channels=True)
async def unlock(interaction: discord.Interaction, channel: discord.TextChannel = None):
    channel = channel or interaction.channel
    await channel.set_permissions(interaction.guild.default_role, send_messages=True)
    await interaction.response.send_message(f'🔓 Unlocked {channel.mention}')

# ============================================
# UTILITY COMMANDS
# ============================================

@bot.tree.command(name='userinfo', description='Get user information')
@app_commands.describe(member='User to get info about')
async def userinfo(interaction: discord.Interaction, member: discord.Member = None):
    member = member or interaction.user
    embed = discord.Embed(title=f'👤 {member.name}', color=member.color)
    embed.add_field(name='ID', value=member.id, inline=True)
    embed.add_field(name='Joined', value=member.joined_at.strftime('%Y-%m-%d') if member.joined_at else 'Unknown', inline=True)
    embed.add_field(name='Created', value=member.created_at.strftime('%Y-%m-%d'), inline=True)
    embed.add_field(name='Roles', value=len(member.roles) - 1, inline=True)
    embed.set_thumbnail(url=member.avatar.url if member.avatar else member.default_avatar.url)
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name='serverinfo', description='Get server information')
async def serverinfo(interaction: discord.Interaction):
    guild = interaction.guild
    embed = discord.Embed(title=f'📊 {guild.name}', color=discord.Color.blue())
    embed.add_field(name='Owner', value=guild.owner.mention if guild.owner else 'Unknown', inline=True)
    embed.add_field(name='Members', value=guild.member_count, inline=True)
    embed.add_field(name='Channels', value=len(guild.channels), inline=True)
    embed.add_field(name='Roles', value=len(guild.roles), inline=True)
    embed.add_field(name='Created', value=guild.created_at.strftime('%Y-%m-%d'), inline=True)
    if guild.icon:
        embed.set_thumbnail(url=guild.icon.url)
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name='avatar', description='Get user avatar')
@app_commands.describe(member='User to get avatar of')
async def avatar(interaction: discord.Interaction, member: discord.Member = None):
    member = member or interaction.user
    embed = discord.Embed(title=f'🖼️ {member.name}\'s Avatar', color=discord.Color.blue())
    embed.set_image(url=member.avatar.url if member.avatar else member.default_avatar.url)
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name='poll', description='Create a poll')
@app_commands.describe(question='Poll question')
async def poll(interaction: discord.Interaction, question: str):
    embed = discord.Embed(title='📊 Poll', description=question, color=discord.Color.blue())
    embed.set_footer(text=f'Poll by {interaction.user.name}')
    await interaction.response.send_message(embed=embed)
    msg = await interaction.original_response()
    await msg.add_reaction('✅')
    await msg.add_reaction('❌')

@bot.tree.command(name='remind', description='Set a reminder')
@app_commands.describe(minutes='Minutes from now', message='Reminder message')
async def remind(interaction: discord.Interaction, minutes: int, message: str):
    await interaction.response.send_message(f'⏰ Reminder set for {minutes} minutes!', ephemeral=True)
    await asyncio.sleep(minutes * 60)
    await interaction.user.send(f'⏰ Reminder: {message}')

# ============================================
# LEVELING COMMANDS
# ============================================

@bot.tree.command(name='rank', description='Check your rank')
@app_commands.describe(member='Member to check')
async def rank(interaction: discord.Interaction, member: discord.Member = None):
    member = member or interaction.user
    embed = discord.Embed(title=f'📊 {member.name}\'s Rank', description='Leveling coming soon!', color=discord.Color.green())
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name='daily', description='Claim daily reward')
async def daily(interaction: discord.Interaction):
    embed = discord.Embed(title='💰 Daily Reward', description='You claimed 100 coins!', color=discord.Color.gold())
    await interaction.response.send_message(embed=embed)

# ============================================
# AUTO MOD - FILTER WORDS
# ============================================

@bot.tree.command(name='filter', description='Manage filtered words')
@app_commands.default_permissions(manage_messages=True)
@app_commands.choices(action=[
    app_commands.Choice(name='add', value='add'),
    app_commands.Choice(name='remove', value='remove'),
    app_commands.Choice(name='list', value='list')
])
async def filter_cmd(interaction: discord.Interaction, action: str, word: str = None):
    config = load_config(interaction.guild_id)
    
    if action == 'add' and word:
        if word not in config['filtered_words']:
            config['filtered_words'].append(word)
            save_config(interaction.guild_id)
            await interaction.response.send_message(f'✅ Added `{word}` to filter list')
    elif action == 'remove' and word:
        if word in config['filtered_words']:
            config['filtered_words'].remove(word)
            save_config(interaction.guild_id)
            await interaction.response.send_message(f'✅ Removed `{word}` from filter list')
    elif action == 'list':
        words = '\n'.join(config['filtered_words']) if config['filtered_words'] else 'No filtered words'
        await interaction.response.send_message(f'**Filtered Words:**\n{words}')
    else:
        await interaction.response.send_message('❌ Invalid usage. Use `/filter add word` or `/filter remove word`')

# ============================================
# EVENT HANDLERS
# ============================================

@bot.event
async def on_message(message):
    if message.author.bot:
        return
    
    # Auto-mod filter
    config = load_config(message.guild.id)
    for word in config['filtered_words']:
        if word.lower() in message.content.lower():
            await message.delete()
            await message.channel.send(f'❌ {message.author.mention}, that word is not allowed!', delete_after=3)
            break
    
    await bot.process_commands(message)

@bot.event
async def on_member_join(member):
    config = load_config(member.guild.id)
    
    # Auto roles
    for role_id in config['auto_roles']:
        role = member.guild.get_role(role_id)
        if role:
            await member.add_roles(role)
    
    # Welcome message
    if config['welcome_channel']:
        channel = member.guild.get_channel(config['welcome_channel'])
        if channel:
            msg = config['welcome_message'].replace('{member}', member.mention).replace('{server}', member.guild.name)
            await channel.send(msg)

# ============================================
# RUN
# ============================================

if __name__ == "__main__":
    bot.run(BOT_TOKEN)

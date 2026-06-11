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

# ============================================
# BOT SETUP - MUST BE FIRST
# ============================================

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
dm_messages = {}
dm_cooldown = {}

def load_config(guild_id):
    guild_id = str(guild_id)
    if guild_id not in server_configs:
        try:
            with open(f"config_{guild_id}.json", "r") as f:
                server_configs[guild_id] = json.load(f)
        except:
            server_configs[guild_id] = {
                "mod_log_channel": None,
                "control_channel": None,
                "filtered_words": [],
                "warn_limit": 3,
                "auto_roles": [],
                "welcome_channel": None,
                "welcome_message": "Welcome {member} to {server}! 🎉",
            }
            save_config(guild_id)
    return server_configs[guild_id]

def save_config(guild_id):
    with open(f"config_{guild_id}.json", "w") as f:
        json.dump(server_configs[str(guild_id)], f, indent=4)

# ============================================
# EVENTS
# ============================================

@bot.event
async def on_ready():
    print(f'✅ {bot.user} is online!')
    try:
        synced = await bot.tree.sync()
        print(f'✅ Synced {len(synced)} slash commands')
    except Exception as e:
        print(f'❌ Failed to sync: {e}')

@bot.event
async def on_message(message):
    if message.author.bot:
        return
    
    # Handle DMs to the bot
    if isinstance(message.channel, discord.DMChannel):
        if message.author.id not in dm_messages:
            dm_messages[message.author.id] = []
        
        dm_messages[message.author.id].append({
            "content": message.content,
            "time": datetime.now(),
            "direction": "incoming"
        })
        
        for guild in bot.guilds:
            config = load_config(guild.id)
            control_channel_id = config.get('control_channel')
            if control_channel_id:
                channel = bot.get_channel(control_channel_id)
                if channel:
                    embed = discord.Embed(
                        title=f"📩 New DM from {message.author.name}",
                        description=f"**Message:** {message.content[:500]}",
                        color=discord.Color.blue(),
                        timestamp=datetime.now()
                    )
                    embed.add_field(name="User ID", value=message.author.id, inline=True)
                    embed.add_field(name="Reply", value=f"Use `/reply {message.author.id} <message>`", inline=False)
                    await channel.send(embed=embed)
        
        if message.content.lower() == 'ping':
            await message.channel.send('pong')
        return
    
    # Auto-mod filter for server messages
    if message.guild:
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
    for role_id in config['auto_roles']:
        role = member.guild.get_role(role_id)
        if role:
            await member.add_roles(role)
    if config['welcome_channel']:
        channel = member.guild.get_channel(config['welcome_channel'])
        if channel:
            msg = config['welcome_message'].replace('{member}', member.mention).replace('{server}', member.guild.name)
            await channel.send(msg)

# ============================================
# COMMAND SYNC
# ============================================

@bot.tree.command(name='refresh', description='Refresh slash commands (Admin only)')
@app_commands.default_permissions(administrator=True)
async def refresh_commands(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)
    try:
        synced = await bot.tree.sync()
        await interaction.followup.send(f'✅ Refreshed {len(synced)} commands!', ephemeral=True)
    except Exception as e:
        await interaction.followup.send(f'❌ Error: {e}', ephemeral=True)

# ============================================
# ANNOUNCEMENT COMMANDS - ADMIN ONLY
# ============================================

@bot.tree.command(name='annc', description='Send a message (Admin only)')
@app_commands.describe(message='The message to send')
@app_commands.default_permissions(administrator=True)
async def announce(interaction: discord.Interaction, message: str):
    """Send a plain text message - Admin only"""
    await interaction.response.send_message("✅ Message sent!", ephemeral=True)
    await interaction.channel.send(message)

@bot.tree.command(name='anncimg', description='Send a message with an image (Admin only)')
@app_commands.describe(
    message='The message to send',
    image_url='Paste the image URL from discord (right-click image → Copy Link)'
)
@app_commands.default_permissions(administrator=True)
async def announce_with_image(interaction: discord.Interaction, message: str, image_url: str):
    """Send a message with an image - Admin only"""
    await interaction.response.send_message("✅ Announcement with image sent!", ephemeral=True)
    await interaction.channel.send(f"{message}\n{image_url}")

@bot.tree.command(name='anncembed', description='Send a fancy embed with image (Admin only)')
@app_commands.describe(
    title='Embed title',
    description='Embed description',
    image_url='Paste image URL here',
    color='Color (red, green, blue, yellow, purple)'
)
@app_commands.default_permissions(administrator=True)
async def announce_embed(interaction: discord.Interaction, title: str, description: str, image_url: str = None, color: str = "blue"):
    """Send a nice embed with optional image - Admin only"""
    
    colors = {
        "red": discord.Color.red(),
        "green": discord.Color.green(),
        "blue": discord.Color.blue(),
        "yellow": discord.Color.yellow(),
        "purple": discord.Color.purple(),
    }
    embed_color = colors.get(color.lower(), discord.Color.blue())
    
    embed = discord.Embed(
        title=f"📢 {title}",
        description=description,
        color=embed_color,
        timestamp=datetime.now()
    )
    if image_url:
        embed.set_image(url=image_url)
    embed.set_footer(text=f"Announced by {interaction.user.name}")
    
    await interaction.response.send_message("✅ Embed announcement sent!", ephemeral=True)
    await interaction.channel.send(embed=embed)

@bot.tree.command(name='anncf', description='Upload a file from your computer (Admin only)')
@app_commands.describe(message='The message to send with your file')
@app_commands.default_permissions(administrator=True)
async def announce_with_file(interaction: discord.Interaction, message: str):
    """Upload a file from your computer - Admin only"""
    
    await interaction.response.send_message(
        "📎 **Now upload your file**\n"
        "1. Type your message above\n"
        "2. Click the + button\n"
        "3. Upload your image/file\n"
        "4. Send the message\n\n"
        f"Message to send: `{message}`",
        ephemeral=True
    )
    
    def check(m):
        return m.author == interaction.user and m.channel == interaction.channel and m.attachments
    
    try:
        msg = await bot.wait_for('message', timeout=60, check=check)
        attachment = msg.attachments[0]
        
        await interaction.channel.send(content=message, file=await attachment.to_file())
        await interaction.followup.send("✅ Announcement with file sent!", ephemeral=True)
        
    except asyncio.TimeoutError:
        await interaction.followup.send("❌ Timed out. Please try again.", ephemeral=True)

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
# DM COMMANDS
# ============================================

@bot.tree.command(name='dm', description='Direct message a user')
@app_commands.describe(user='The user to message', message='The message to send')
@app_commands.default_permissions(administrator=True)
async def dm_user(interaction: discord.Interaction, user: discord.User, message: str):
    if interaction.user.id in dm_cooldown:
        time_diff = (datetime.now() - dm_cooldown[interaction.user.id]).total_seconds()
        if time_diff < 5:
            await interaction.response.send_message(f'⏰ Please wait {5 - int(time_diff)} seconds', ephemeral=True)
            return
    
    dm_cooldown[interaction.user.id] = datetime.now()
    
    embed = discord.Embed(title=f"📬 Message from {interaction.guild.name} Staff", description=message, color=discord.Color.blue())
    embed.add_field(name="Sent by", value=interaction.user.mention, inline=True)
    
    try:
        await user.send(embed=embed)
        await interaction.response.send_message(f'✅ Message sent to {user.mention}', ephemeral=True)
    except discord.Forbidden:
        await interaction.response.send_message(f'❌ Cannot DM {user.mention} - DMs disabled', ephemeral=True)
    except Exception as e:
        await interaction.response.send_message(f'❌ Error: {str(e)[:100]}', ephemeral=True)

@bot.tree.command(name='reply', description='Reply to a user via DM')
@app_commands.describe(user_id='The user ID to reply to', message='The message to send')
@app_commands.default_permissions(administrator=True)
async def reply_to_user(interaction: discord.Interaction, user_id: str, message: str):
    try:
        user = await bot.fetch_user(int(user_id))
        embed = discord.Embed(title=f"📬 Reply from {interaction.guild.name} Staff", description=message, color=discord.Color.green())
        await user.send(embed=embed)
        
        if int(user_id) not in dm_messages:
            dm_messages[int(user_id)] = []
        dm_messages[int(user_id)].append({"content": f"[REPLY] {message}", "time": datetime.now(), "direction": "outgoing"})
        
        await interaction.response.send_message(f"✅ Message sent to {user.name}", ephemeral=True)
    except Exception as e:
        await interaction.response.send_message(f"❌ Error: {str(e)[:100]}", ephemeral=True)

@bot.tree.command(name='conversations', description='View all active DM conversations')
@app_commands.default_permissions(administrator=True)
async def list_conversations(interaction: discord.Interaction):
    if not dm_messages:
        await interaction.response.send_message("📭 No active conversations.", ephemeral=True)
        return
    
    embed = discord.Embed(title="📋 Active DM Conversations", description=f"Total: {len(dm_messages)} users", color=discord.Color.blue())
    for user_id, messages in list(dm_messages.items())[:15]:
        try:
            user = await bot.fetch_user(user_id)
            name = user.name
        except:
            name = f"Unknown ({user_id})"
        last_msg = messages[-1]["content"][:40] if messages else "None"
        embed.add_field(name=f"👤 {name}", value=f"ID: `{user_id}`\nLast: {last_msg}\nMessages: {len(messages)}", inline=False)
    
    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name='setcontrol', description='Set channel for DM notifications')
@app_commands.describe(channel='The channel to send DM notifications to')
@app_commands.default_permissions(administrator=True)
async def set_control_channel(interaction: discord.Interaction, channel: discord.TextChannel):
    config = load_config(interaction.guild_id)
    config['control_channel'] = channel.id
    save_config(interaction.guild_id)
    await interaction.response.send_message(f"✅ DM notifications will be sent to {channel.mention}", ephemeral=True)

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
        await interaction.response.send_message('❌ Use `/filter add word` or `/filter remove word`')

# ============================================
# RUN
# ============================================

if __name__ == "__main__":
    bot.run(BOT_TOKEN)

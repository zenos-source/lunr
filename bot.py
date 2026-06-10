# ============================================
# CONTROL PANEL - DM MONITORING
# ============================================

# Store DM conversations
dm_messages = {}

@bot.event
async def on_message(message):
    # Handle DMs to the bot
    if isinstance(message.channel, discord.DMChannel) and message.author != bot.user:
        
        # Store the message
        if message.author.id not in dm_messages:
            dm_messages[message.author.id] = []
        
        dm_messages[message.author.id].append({
            "content": message.content,
            "time": datetime.now(),
            "direction": "incoming"
        })
        
        # Notify control channel if set
        config = load_config(message.author.id)  # Use user ID as key for DM tracking
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
        
        # Auto-respond (optional)
        if message.content.lower() == 'ping':
            await message.channel.send('pong')
        
        return
    
    await bot.process_commands(message)


@bot.tree.command(name='control', description='Open control panel to monitor DMs')
@app_commands.default_permissions(administrator=True)
async def control_panel(interaction: discord.Interaction):
    """Main control panel for DM monitoring"""
    
    embed = discord.Embed(
        title="🎮 DM Control Panel",
        description="Monitor and reply to user DMs",
        color=discord.Color.blue()
    )
    embed.add_field(name="📊 Active Conversations", value=f"{len(dm_messages)} users", inline=True)
    embed.add_field(name="💬 Total Messages", value=f"{sum(len(msg) for msg in dm_messages.values())}", inline=True)
    embed.add_field(name="📌 Commands", value="`/conversations` - View all conversations\n`/reply <user> <msg>` - Reply to user\n`/setcontrol <#channel>` - Set notification channel", inline=False)
    
    view = ControlView()
    await interaction.response.send_message(embed=embed, view=view, ephemeral=True)


class ControlView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=60)
    
    @discord.ui.button(label="📋 View Conversations", style=discord.ButtonStyle.primary, emoji="📋")
    async def view_conversations(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not dm_messages:
            await interaction.response.send_message("No active conversations.", ephemeral=True)
            return
        
        embed = discord.Embed(title="📋 Active Conversations", color=discord.Color.blue())
        
        for user_id, messages in list(dm_messages.items())[:10]:
            user = await bot.fetch_user(user_id)
            last_msg = messages[-1]["content"][:50] if messages else "No messages"
            embed.add_field(
                name=f"{user.name} (ID: {user_id})",
                value=f"Last: {last_msg}\nMessages: {len(messages)}",
                inline=False
            )
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
    
    @discord.ui.button(label="💬 Quick Reply", style=discord.ButtonStyle.success, emoji="💬")
    async def quick_reply(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message(
            "**Quick Reply**\nUse `/reply <user_id> <message>`\n\nExample: `/reply 123456789 Hello!`",
            ephemeral=True
        )


@bot.tree.command(name='conversations', description='View all active DM conversations')
@app_commands.default_permissions(administrator=True)
async def list_conversations(interaction: discord.Interaction):
    """List all users who have DMed the bot"""
    
    if not dm_messages:
        await interaction.response.send_message("📭 No active conversations.", ephemeral=True)
        return
    
    embed = discord.Embed(
        title="📋 Active DM Conversations",
        description=f"Total: {len(dm_messages)} users",
        color=discord.Color.blue()
    )
    
    for user_id, messages in list(dm_messages.items())[:15]:
        try:
            user = await bot.fetch_user(user_id)
            name = user.name
        except:
            name = f"Unknown ({user_id})"
        
        last_msg = messages[-1]["content"][:40] if messages else "None"
        embed.add_field(
            name=f"👤 {name}",
            value=f"ID: `{user_id}`\nLast: {last_msg}\nMessages: {len(messages)}",
            inline=False
        )
    
    await interaction.response.send_message(embed=embed, ephemeral=True)


@bot.tree.command(name='reply', description='Reply to a user via DM')
@app_commands.describe(
    user_id='The user ID to reply to',
    message='The message to send'
)
@app_commands.default_permissions(administrator=True)
async def reply_to_user(interaction: discord.Interaction, user_id: str, message: str):
    """Reply to a user who DMed the bot"""
    
    try:
        user = await bot.fetch_user(int(user_id))
        
        embed = discord.Embed(
            title=f"📬 Reply from {interaction.guild.name} Staff",
            description=message,
            color=discord.Color.green()
        )
        embed.add_field(name="Sent by", value=interaction.user.name, inline=True)
        embed.set_footer(text="Reply to this message to continue the conversation")
        
        await user.send(embed=embed)
        
        # Store the reply
        if int(user_id) not in dm_messages:
            dm_messages[int(user_id)] = []
        
        dm_messages[int(user_id)].append({
            "content": f"[REPLY] {message}",
            "time": datetime.now(),
            "direction": "outgoing"
        })
        
        await interaction.response.send_message(f"✅ Message sent to {user.name}", ephemeral=True)
        
    except discord.Forbidden:
        await interaction.response.send_message(f"❌ Cannot DM user - they may have DMs disabled", ephemeral=True)
    except ValueError:
        await interaction.response.send_message(f"❌ Invalid user ID: {user_id}", ephemeral=True)
    except Exception as e:
        await interaction.response.send_message(f"❌ Error: {str(e)[:100]}", ephemeral=True)


@bot.tree.command(name='setcontrol', description='Set channel for DM notifications')
@app_commands.describe(channel='The channel to send DM notifications to')
@app_commands.default_permissions(administrator=True)
async def set_control_channel(interaction: discord.Interaction, channel: discord.TextChannel):
    """Set which channel gets DM notifications"""
    
    # Store control channel in config
    config = load_config(interaction.guild_id)
    config['control_channel'] = channel.id
    save_config(interaction.guild_id)
    
    await interaction.response.send_message(f"✅ DM notifications will be sent to {channel.mention}", ephemeral=True)


@bot.tree.command(name='viewdm', description='View conversation with a specific user')
@app_commands.describe(user_id='The user ID to view conversation with')
@app_commands.default_permissions(administrator=True)
async def view_conversation(interaction: discord.Interaction, user_id: str):
    """View full DM history with a user"""
    
    try:
        uid = int(user_id)
        user = await bot.fetch_user(uid)
        
        if uid not in dm_messages or not dm_messages[uid]:
            await interaction.response.send_message(f"No conversation found with {user.name}", ephemeral=True)
            return
        
        embed = discord.Embed(
            title=f"💬 Conversation with {user.name}",
            color=discord.Color.blue()
        )
        
        conversation = ""
        for msg in dm_messages[uid][-20:]:  # Last 20 messages
            direction = "📩" if msg["direction"] == "incoming" else "📤"
            time_str = msg["time"].strftime("%H:%M")
            conversation += f"{direction} **{time_str}:** {msg['content'][:100]}\n"
        
        embed.description = conversation or "No messages"
        await interaction.response.send_message(embed=embed, ephemeral=True)
        
    except Exception as e:
        await interaction.response.send_message(f"❌ Error: {str(e)[:100]}", ephemeral=True)


@bot.tree.command(name='clearconv', description='Clear conversation history with a user')
@app_commands.describe(user_id='The user ID to clear conversation with')
@app_commands.default_permissions(administrator=True)
async def clear_conversation(interaction: discord.Interaction, user_id: str):
    """Clear DM history with a user"""
    
    try:
        uid = int(user_id)
        
        if uid in dm_messages:
            del dm_messages[uid]
            await interaction.response.send_message(f"✅ Cleared conversation with user ID {user_id}", ephemeral=True)
        else:
            await interaction.response.send_message(f"No conversation found with ID {user_id}", ephemeral=True)
            
    except Exception as e:
        await interaction.response.send_message(f"❌ Error: {str(e)[:100]}", ephemeral=True)

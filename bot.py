# ============================================
# ANNOUNCEMENT COMMANDS - REAL MESSAGE STYLE
# ============================================

@bot.tree.command(name='annc', description='Send a message as the bot (looks like a real message)')
@app_commands.describe(
    message='The message to send'
)
@app_commands.default_permissions(administrator=True)
async def announce(interaction: discord.Interaction, message: str):
    """Send a message that looks like a real user message (no embed)"""
    
    await interaction.response.send_message("✅ Message sent!", ephemeral=True)
    await interaction.channel.send(message)


@bot.tree.command(name='anncembed', description='Send an embed announcement')
@app_commands.describe(
    title='Announcement title',
    message='The announcement message',
    color='Color (red, green, blue, yellow, purple)'
)
@app_commands.default_permissions(administrator=True)
async def announce_embed(interaction: discord.Interaction, title: str, message: str, color: str = "blue"):
    """Send an embed announcement with optional color"""
    
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
        description=message,
        color=embed_color,
        timestamp=datetime.now()
    )
    embed.set_footer(text=f"Announced by {interaction.user.name}")
    
    await interaction.response.send_message("✅ Announcement sent!", ephemeral=True)
    await interaction.channel.send(embed=embed)


@bot.tree.command(name='anncimage', description='Send an announcement with an image')
@app_commands.describe(
    message='The message to send',
    image_url='URL of the image to attach'
)
@app_commands.default_permissions(administrator=True)
async def announce_image(interaction: discord.Interaction, message: str, image_url: str):
    """Send a message with an image attachment"""
    
    await interaction.response.send_message("✅ Announcement sent!", ephemeral=True)
    await interaction.channel.send(content=message, file=None)
    
    # Send image separately
    embed = discord.Embed()
    embed.set_image(url=image_url)
    await interaction.channel.send(embed=embed)


@bot.tree.command(name='anncfile', description='Send a message with a file attachment')
@app_commands.describe(
    message='The message to send'
)
@app_commands.default_permissions(administrator=True)
async def announce_file(interaction: discord.Interaction, message: str):
    """Send a message and wait for file attachment"""
    
    await interaction.response.send_message(
        "📎 Please upload the file you want to attach.\nYou have 60 seconds.", 
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

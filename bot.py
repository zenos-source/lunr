# ============================================
# ANNOUNCEMENT COMMAND
# ============================================

@bot.tree.command(name='annc', description='Send an announcement in the current channel')
@app_commands.describe(
    message='The announcement message to send',
    ping_role='Optional role to ping (optional)'
)
@app_commands.default_permissions(administrator=True)
async def announce(interaction: discord.Interaction, message: str, ping_role: discord.Role = None):
    """Send an announcement in the channel where the command is used"""
    
    # Create announcement embed
    embed = discord.Embed(
        title="📢 Announcement",
        description=message,
        color=discord.Color.blue(),
        timestamp=datetime.now()
    )
    embed.set_footer(text=f"Announced by {interaction.user.name}")
    
    # Send the announcement
    if ping_role:
        await interaction.response.send_message(f"✅ Announcement sent! (Pinging {ping_role.mention})", ephemeral=True)
        await interaction.channel.send(content=ping_role.mention, embed=embed)
    else:
        await interaction.response.send_message("✅ Announcement sent!", ephemeral=True)
        await interaction.channel.send(embed=embed)


@bot.tree.command(name='anncembed', description='Send a custom embed announcement')
@app_commands.describe(
    title='Embed title',
    description='Embed description',
    color='Color in hex (optional)',
    footer='Footer text (optional)'
)
@app_commands.default_permissions(administrator=True)
async def announce_embed(
    interaction: discord.Interaction, 
    title: str, 
    description: str, 
    color: str = None, 
    footer: str = None
):
    """Send a custom embed announcement"""
    
    # Parse color
    embed_color = discord.Color.blue()
    if color:
        try:
            embed_color = int(color.replace('#', ''), 16)
        except:
            embed_color = discord.Color.blue()
    
    # Create custom embed
    embed = discord.Embed(
        title=title,
        description=description,
        color=embed_color,
        timestamp=datetime.now()
    )
    embed.set_footer(text=footer or f"Announced by {interaction.user.name}")
    
    await interaction.response.send_message("✅ Custom announcement sent!", ephemeral=True)
    await interaction.channel.send(embed=embed)


@bot.tree.command(name='annctitle', description='Send an announcement with a custom title')
@app_commands.describe(
    title='Announcement title',
    message='Announcement message',
    ping_role='Optional role to ping'
)
@app_commands.default_permissions(administrator=True)
async def announce_title(
    interaction: discord.Interaction, 
    title: str, 
    message: str, 
    ping_role: discord.Role = None
):
    """Send an announcement with a custom title"""
    
    embed = discord.Embed(
        title=f"📢 {title}",
        description=message,
        color=discord.Color.blue(),
        timestamp=datetime.now()
    )
    embed.set_footer(text=f"Announced by {interaction.user.name}")
    
    if ping_role:
        await interaction.response.send_message(f"✅ Announcement sent! (Pinging {ping_role.mention})", ephemeral=True)
        await interaction.channel.send(content=ping_role.mention, embed=embed)
    else:
        await interaction.response.send_message("✅ Announcement sent!", ephemeral=True)
        await interaction.channel.send(embed=embed)

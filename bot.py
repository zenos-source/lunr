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

# Server configurations (will sync to website later)
server_configs = {}

def load_config(guild_id):
    if str(guild_id) not in server_configs:
        server_configs[str(guild_id)] = {
            "welcome_channel": None,
            "welcome_message": "Welcome {member} to {server}! 🎉",
            "goodbye_channel": None,
            "goodbye_message": "Goodbye {member}! We'll miss you! 👋",
            "mod_log_channel": None,
            "member_log_channel": None,
            "auto_roles": [],
            "prefix": ".",
            "leveling_enabled": True,
            "level_up_channel": None,
            "economy_enabled": True,
            "ticket_category": None,
            "ticket_staff_role": None,
            "mute_role": None,
            "warn_limit": 3,
            "filtered_words": [],
            "ignored_channels": [],
            "admin_roles": [],
            "mod_roles": [],
        }
        save_config(guild_id)
    return server_configs[str(guild_id)]

def save_config(guild_id):
    with open(f"config_{guild_id}.json", "w") as f:
        json.dump(server_configs[str(guild_id)], f, indent=4)

def load_all_configs():
    for file in os.listdir():
        if file.startswith("config_") and file.endswith(".json"):
            guild_id = file.replace("config_", "").replace(".json", "")
            with open(file, "r") as f:
                server_configs[guild_id] = json.load(f)

load_all_configs()

# Store warns, filters, levels
warns = {}
user_levels = {}

# ============================================
# SETUP COMMAND (The Main One)
# ============================================

@bot.tree.command(name='setup', description='Setup the bot for your server')
async def setup(interaction: discord.Interaction):
    """Interactive setup command - like Echo bot"""
    
    config = load_config(interaction.guild_id)
    
    embed = discord.Embed(
        title="🔧 Bot Setup Wizard",
        description="Welcome to the setup wizard! I'll help you configure the bot for your server.\n\n"
                    "Click the buttons below to configure different features.",
        color=discord.Color.blue()
    )
    embed.add_field(name="📊 Current Status", value=f"✅ {len(config)} settings configured", inline=False)
    embed.add_field(name="💡 Need Help?", value="Join our [Support Server](https://discord.gg/support) for help", inline=False)
    
    view = SetupView(interaction.guild_id)
    await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

class SetupView(discord.ui.View):
    def __init__(self, guild_id):
        super().__init__(timeout=120)
        self.guild_id = guild_id
    
    @discord.ui.button(label="👋 Welcome Messages", style=discord.ButtonStyle.primary, emoji="👋", row=0)
    async def welcome_setup(self, interaction: discord.Interaction, button: discord.ui.Button):
        config = load_config(self.guild_id)
        embed = discord.Embed(
            title="👋 Welcome Messages Setup",
            description="Configure welcome messages for new members",
            color=discord.Color.green()
        )
        embed.add_field(name="Current Channel", value=f"<#{config['welcome_channel']}>" if config['welcome_channel'] else "Not set", inline=False)
        embed.add_field(name="Current Message", value=config['welcome_message'], inline=False)
        embed.add_field(name="Variables", value="`{member}` - Member mention\n`{server}` - Server name\n`{count}` - Member count", inline=False)
        
        view = WelcomeSetupView(self.guild_id)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
    
    @discord.ui.button(label="👋 Goodbye Messages", style=discord.ButtonStyle.primary, emoji="👋", row=0)
    async def goodbye_setup(self, interaction: discord.Interaction, button: discord.ui.Button):
        config = load_config(self.guild_id)
        embed = discord.Embed(
            title="👋 Goodbye Messages Setup",
            description="Configure goodbye messages for leaving members",
            color=discord.Color.red()
        )
        embed.add_field(name="Current Channel", value=f"<#{config['goodbye_channel']}>" if config['goodbye_channel'] else "Not set", inline=False)
        embed.add_field(name="Current Message", value=config['goodbye_message'], inline=False)
        
        view = GoodbyeSetupView(self.guild_id)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
    
    @discord.ui.button(label="📜 Mod Logging", style=discord.ButtonStyle.primary, emoji="📜", row=0)
    async def modlog_setup(self, interaction: discord.Interaction, button: discord.ui.Button):
        config = load_config(self.guild_id)
        embed = discord.Embed(
            title="📜 Mod Logging Setup",
            description="Configure logging channels for moderation actions",
            color=discord.Color.blue()
        )
        embed.add_field(name="Mod Log Channel", value=f"<#{config['mod_log_channel']}>" if config['mod_log_channel'] else "Not set", inline=False)
        embed.add_field(name="Member Log Channel", value=f"<#{config['member_log_channel']}>" if config['member_log_channel'] else "Not set", inline=False)
        
        view = ModLogSetupView(self.guild_id)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
    
    @discord.ui.button(label="🛡️ Auto Mod", style=discord.ButtonStyle.primary, emoji="🛡️", row=1)
    async def automod_setup(self, interaction: discord.Interaction, button: discord.ui.Button):
        config = load_config(self.guild_id)
        embed = discord.Embed(
            title="🛡️ Auto Mod Setup",
            description="Configure automatic moderation filters",
            color=discord.Color.orange()
        )
        embed.add_field(name="Filtered Words", value="\n".join(config['filtered_words'][:10]) if config['filtered_words'] else "None", inline=False)
        embed.add_field(name="Warn Limit", value=config['warn_limit'], inline=False)
        
        view = AutoModSetupView(self.guild_id)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
    
    @discord.ui.button(label="🎭 Auto Roles", style=discord.ButtonStyle.primary, emoji="🎭", row=1)
    async def autorole_setup(self, interaction: discord.Interaction, button: discord.ui.Button):
        config = load_config(self.guild_id)
        embed = discord.Embed(
            title="🎭 Auto Roles Setup",
            description="Configure roles automatically assigned to new members",
            color=discord.Color.purple()
        )
        roles_str = "\n".join([f"<@&{role_id}>" for role_id in config['auto_roles']]) if config['auto_roles'] else "None"
        embed.add_field(name="Auto Roles", value=roles_str, inline=False)
        
        view = AutoRoleSetupView(self.guild_id)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
    
    @discord.ui.button(label="💬 Leveling", style=discord.ButtonStyle.primary, emoji="💬", row=1)
    async def leveling_setup(self, interaction: discord.Interaction, button: discord.ui.Button):
        config = load_config(self.guild_id)
        embed = discord.Embed(
            title="💬 Leveling Setup",
            description="Configure XP and leveling system",
            color=discord.Color.gold()
        )
        embed.add_field(name="Enabled", value="✅ Yes" if config['leveling_enabled'] else "❌ No", inline=False)
        embed.add_field(name="Level Up Channel", value=f"<#{config['level_up_channel']}>" if config['level_up_channel'] else "Same channel", inline=False)
        
        view = LevelingSetupView(self.guild_id)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
    
    @discord.ui.button(label="🎫 Tickets", style=discord.ButtonStyle.primary, emoji="🎫", row=2)
    async def tickets_setup(self, interaction: discord.Interaction, button: discord.ui.Button):
        config = load_config(self.guild_id)
        embed = discord.Embed(
            title="🎫 Ticket System Setup",
            description="Configure support ticket system",
            color=discord.Color.blurple()
        )
        embed.add_field(name="Category", value=f"<#{config['ticket_category']}>" if config['ticket_category'] else "Not set", inline=False)
        embed.add_field(name="Staff Role", value=f"<@&{config['ticket_staff_role']}>" if config['ticket_staff_role'] else "Not set", inline=False)
        
        view = TicketsSetupView(self.guild_id)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
    
    @discord.ui.button(label="✅ Finish Setup", style=discord.ButtonStyle.success, emoji="✅", row=2)
    async def finish_setup(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(
            title="✅ Setup Complete!",
            description="Your server has been configured!\n\n"
                        "You can always change settings using the `/settings` command.\n\n"
                        "**Next Steps:**\n"
                        "1️⃣ Type `/panel` to open the control panel\n"
                        "2️⃣ Connect your Discord account to our website for advanced controls\n"
                        "3️⃣ Invite your friends and start using the bot!",
            color=discord.Color.green()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

# ============================================
# SETUP VIEWS (Channel/Message Selectors)
# ============================================

class WelcomeSetupView(discord.ui.View):
    def __init__(self, guild_id):
        super().__init__(timeout=60)
        self.guild_id = guild_id
    
    @discord.ui.select(placeholder="Select welcome channel", options=[])
    async def select_channel(self, interaction: discord.Interaction, select: discord.ui.Select):
        config = load_config(self.guild_id)
        config['welcome_channel'] = int(select.values[0])
        save_config(self.guild_id)
        await interaction.response.send_message(f"✅ Welcome channel set to <#{select.values[0]}>", ephemeral=True)

# Similar views for other settings...
# (I'll add all of them)

# ============================================
# PANEL COMMAND (For website integration later)
# ============================================

@bot.tree.command(name='panel', description='Open the control panel')
async def panel(interaction: discord.Interaction):
    """Open the control panel - will connect to website"""
    
    embed = discord.Embed(
        title="🎮 Control Panel",
        description="Manage your server settings",
        color=discord.Color.blue()
    )
    embed.add_field(name="📊 Dashboard", value="[Click here to open web dashboard](https://your-website.com/dashboard)", inline=False)
    embed.add_field(name="🔗 Connect Account", value="Use the website to link your Discord account for advanced controls", inline=False)
    embed.set_footer(text="Coming soon: Full web integration!")
    
    view = discord.ui.View()
    view.add_item(discord.ui.Button(label="Open Web Dashboard", url="https://your-website.com/dashboard", style=discord.ButtonStyle.link))
    
    await interaction.response.send_message(embed=embed, view=view)

# ============================================
# RUN
# ============================================

if __name__ == "__main__":
    bot.run(BOT_TOKEN)

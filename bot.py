import discord
from discord.ext import commands
from discord.ui import Button, View
import json
import hashlib
import time
from datetime import datetime, timedelta

BOT_TOKEN = "YOUR_TOKEN"

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)

# Store keys and users
keys = {
    "XXX-XXX-XXX": {"days": 30, "used": False, "user": None, "hwid": None},
}

users = {}  # user_id: {"key": "xxx", "expires": timestamp, "hwid": "xxx"}

# ============================================
# PAYMENT COMMANDS (For you, the seller)
# ============================================

@bot.command()
@commands.has_permissions(administrator=True)
async def gen(ctx, days: int, amount: int = 1):
    """Generate keys: !gen 30 5"""
    for _ in range(amount):
        key = f"{hashlib.md5(f'{time.time()}{_}'.encode()).hexdigest()[:8].upper()}"
        keys[key] = {"days": days, "used": False, "user": None, "hwid": None}
        
        # DM the buyer (if you specify user)
        if amount == 1 and ctx.message.mentions:
            await ctx.message.mentions[0].send(f"✅ Your {days}-day key: `{key}`")
    
    await ctx.send(f"✅ Generated {amount} key(s) for {days} days")

@bot.command()
@commands.has_permissions(administrator=True)
async def checkkey(ctx, key: str):
    """Check if key is valid"""
    if key in keys:
        k = keys[key]
        await ctx.send(f"Key: {key}\nDays: {k['days']}\nUsed: {k['used']}\nUser: {k['user']}")
    else:
        await ctx.send("Key not found")

# ============================================
# USER COMMANDS (What customers use)
# ============================================

class PanelView(View):
    def __init__(self, user_id):
        super().__init__(timeout=None)
        self.user_id = user_id
    
    @discord.ui.button(label="🎫 Redeem Key", style=discord.ButtonStyle.success)
    async def redeem(self, interaction: discord.Interaction, button: Button):
        if interaction.user.id != self.user_id:
            return await interaction.response.send_message("Not for you", ephemeral=True)
        
        await interaction.response.send_message("Type your key in chat (60s):", ephemeral=True)
        
        def check(m):
            return m.author.id == self.user_id and m.channel == interaction.channel
        
        try:
            msg = await bot.wait_for('message', timeout=60, check=check)
            key = msg.content.strip().upper()
            
            if key in keys and not keys[key]["used"]:
                # Activate key
                expiry = datetime.now() + timedelta(days=keys[key]["days"])
                users[str(self.user_id)] = {
                    "key": key,
                    "expires": expiry.timestamp(),
                    "hwid": None
                }
                keys[key]["used"] = True
                keys[key]["user"] = str(self.user_id)
                
                await interaction.followup.send(f"✅ Activated! {keys[key]['days']} days added.", ephemeral=True)
            else:
                await interaction.followup.send("❌ Invalid or used key", ephemeral=True)
        except:
            await interaction.followup.send("❌ Timed out", ephemeral=True)
    
    @discord.ui.button(label="🔑 Set HWID", style=discord.ButtonStyle.primary)
    async def set_hwid(self, interaction: discord.Interaction, button: Button):
        if interaction.user.id != self.user_id:
            return
        
        await interaction.response.send_message("Send your HWID (60s):", ephemeral=True)
        
        def check(m):
            return m.author.id == self.user_id and m.channel == interaction.channel
        
        try:
            msg = await bot.wait_for('message', timeout=60, check=check)
            hwid = msg.content.strip()
            
            if str(self.user_id) in users:
                users[str(self.user_id)]["hwid"] = hwid
                await interaction.followup.send(f"✅ HWID set: `{hwid[:10]}...`", ephemeral=True)
            else:
                await interaction.followup.send("❌ No active subscription", ephemeral=True)
        except:
            await interaction.followup.send("❌ Timed out", ephemeral=True)
    
    @discord.ui.button(label="📜 Get Script", style=discord.ButtonStyle.primary)
    async def get_script(self, interaction: discord.Interaction, button: Button):
        if interaction.user.id != self.user_id:
            return
        
        user_id = str(self.user_id)
        
        if user_id not in users:
            return await interaction.response.send_message("❌ No active key. Redeem one first!", ephemeral=True)
        
        user = users[user_id]
        if datetime.now().timestamp() > user["expires"]:
            return await interaction.response.send_message("❌ Key expired! Buy a new one.", ephemeral=True)
        
        if not user["hwid"]:
            return await interaction.response.send_message("❌ Set HWID first using /sethwid", ephemeral=True)
        
        # Check HWID matches (in real bot, compare with actual HWID)
        
        days_left = int((user["expires"] - datetime.now().timestamp()) / 86400)
        
        script = f"""
        -- FLASH TP Loader
        -- HWID: {user["hwid"]}
        -- Expires: {days_left} days
        
        loadstring(game:HttpGet("https://your-api.com/script?key={user["key"]}"))()
        """
        
        await interaction.response.send_message(f"```lua\n{script}```", ephemeral=True)
    
    @discord.ui.button(label="📊 Status", style=discord.ButtonStyle.secondary)
    async def status(self, interaction: discord.Interaction, button: Button):
        if interaction.user.id != self.user_id:
            return
        
        user_id = str(self.user_id)
        
        if user_id not in users:
            return await interaction.response.send_message("❌ No active subscription", ephemeral=True)
        
        user = users[user_id]
        expires = datetime.fromtimestamp(user["expires"])
        days_left = max(0, (user["expires"] - datetime.now().timestamp()) / 86400)
        
        embed = discord.Embed(title="📊 Subscription Status", color=discord.Color.green() if days_left > 0 else discord.Color.red())
        embed.add_field(name="Status", value="✅ Active" if days_left > 0 else "❌ Expired")
        embed.add_field(name="Expires", value=expires.strftime("%Y-%m-%d"))
        embed.add_field(name="Days Left", value=f"{int(days_left)}")
        embed.add_field(name="HWID Set", value="✅ Yes" if user["hwid"] else "❌ No")
        
        await interaction.response.send_message(embed=embed, ephemeral=True)

# ============================================
# MAIN COMMANDS
# ============================================

@bot.command()
async def panel(ctx):
    """Open the control panel"""
    view = PanelView(ctx.author.id)
    
    embed = discord.Embed(
        title="🔐 FLASH TP Control Panel",
        description="Redeem keys and manage your subscription",
        color=discord.Color.blue()
    )
    
    await ctx.send(embed=embed, view=view)

@bot.command()
async def buy(ctx):
    """Get purchase link"""
    await ctx.send("💸 **Buy keys here:** https://your-store.com\n\nDM <@owner> for bulk pricing")

# ============================================
# RUN
# ============================================

if __name__ == "__main__":
    bot.run(BOT_TOKEN)

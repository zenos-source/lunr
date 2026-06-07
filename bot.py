import discord
from discord.ext import commands
from discord import app_commands
import sqlite3
import secrets
import json
import os
from datetime import datetime, timedelta

TOKEN = os.getenv("DISCORD_TOKEN")
OWNER_ID = int(os.getenv("OWNER_ID", 0))

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix='.', intents=intents)

# Database setup
conn = sqlite3.connect('whitelist.db')
c = conn.cursor()
c.execute('''CREATE TABLE IF NOT EXISTS users (
    discord_id TEXT PRIMARY KEY,
    username TEXT,
    whitelisted INTEGER DEFAULT 0,
    expires_at TEXT,
    hwid TEXT,
    products TEXT
)''')
c.execute('''CREATE TABLE IF NOT EXISTS keys (
    code TEXT PRIMARY KEY,
    duration INTEGER,
    used INTEGER DEFAULT 0,
    used_by TEXT,
    created_at TEXT
)''')
c.execute('''CREATE TABLE IF NOT EXISTS products (
    id TEXT PRIMARY KEY,
    name TEXT,
    script_url TEXT
)''')
conn.commit()

def is_owner(interaction):
    return interaction.user.id == OWNER_ID

@bot.event
async def on_ready():
    await bot.tree.sync()
    print(f"✅ Luarmor Bot ready - {bot.user}")

# ========== USER COMMANDS ==========

@bot.tree.command(name="redeem", description="Redeem a key to whitelist yourself")
@app_commands.describe(key="Your activation key")
async def redeem(interaction: discord.Interaction, key: str):
    await interaction.response.defer(ephemeral=True)
    
    c.execute("SELECT * FROM keys WHERE code = ?", (key,))
    key_data = c.fetchone()
    
    if not key_data:
        return await interaction.followup.send("❌ Invalid key", ephemeral=True)
    
    if key_data[3] == 1:
        return await interaction.followup.send("❌ Key already used", ephemeral=True)
    
    duration = key_data[1]
    expires_at = None if duration == 0 else (datetime.now() + timedelta(days=duration)).isoformat()
    
    c.execute("INSERT OR REPLACE INTO users (discord_id, username, whitelisted, expires_at) VALUES (?, ?, 1, ?)",
              (str(interaction.user.id), interaction.user.name, expires_at))
    c.execute("UPDATE keys SET used = 1, used_by = ? WHERE code = ?", (str(interaction.user.id), key))
    conn.commit()
    
    await interaction.followup.send(f"✅ Whitelisted! Expires: {expires_at if expires_at else 'Lifetime'}", ephemeral=True)

@bot.tree.command(name="status", description="Check your whitelist status")
async def status(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)
    
    c.execute("SELECT * FROM users WHERE discord_id = ?", (str(interaction.user.id),))
    user = c.fetchone()
    
    if not user or user[2] == 0:
        return await interaction.followup.send("❌ Not whitelisted", ephemeral=True)
    
    if user[3]:
        expires = datetime.fromisoformat(user[3])
        if expires < datetime.now():
            return await interaction.followup.send("❌ Whitelist expired", ephemeral=True)
        days = (expires - datetime.now()).days
        await interaction.followup.send(f"✅ Whitelisted. Expires in {days} days", ephemeral=True)
    else:
        await interaction.followup.send("✅ Whitelisted (Lifetime)", ephemeral=True)

# ========== ADMIN COMMANDS ==========

@bot.tree.command(name="genkey", description="[ADMIN] Generate activation keys")
@app_commands.describe(duration="Days (0 = lifetime)", amount="Number of keys")
async def genkey(interaction: discord.Interaction, duration: int, amount: int = 1):
    if not is_owner(interaction):
        return await interaction.response.send_message("❌ Owner only", ephemeral=True)
    
    await interaction.response.defer(ephemeral=True)
    
    keys = []
    for _ in range(amount):
        code = secrets.token_hex(16).upper()
        c.execute("INSERT INTO keys (code, duration, created_at) VALUES (?, ?, ?)",
                  (code, duration, datetime.now().isoformat()))
        keys.append(code)
    conn.commit()
    
    await interaction.followup.send(f"✅ Generated {amount} key(s) for {duration} days\n```\n" + "\n".join(keys) + "\n```", ephemeral=True)

@bot.tree.command(name="whitelist", description="[ADMIN] Whitelist a user")
@app_commands.describe(user="User to whitelist", days="Days (0 = lifetime)")
async def whitelist_user(interaction: discord.Interaction, user: discord.User, days: int):
    if not is_owner(interaction):
        return await interaction.response.send_message("❌ Owner only", ephemeral=True)
    
    expires = None if days == 0 else (datetime.now() + timedelta(days=days)).isoformat()
    c.execute("INSERT OR REPLACE INTO users (discord_id, username, whitelisted, expires_at) VALUES (?, ?, 1, ?)",
              (str(user.id), user.name, expires))
    conn.commit()
    
    await interaction.response.send_message(f"✅ Whitelisted {user.mention} for {days} days", ephemeral=False)

@bot.tree.command(name="unwhitelist", description="[ADMIN] Remove user from whitelist")
@app_commands.describe(user="User to remove")
async def unwhitelist(interaction: discord.Interaction, user: discord.User):
    if not is_owner(interaction):
        return await interaction.response.send_message("❌ Owner only", ephemeral=True)
    
    c.execute("DELETE FROM users WHERE discord_id = ?", (str(user.id),))
    conn.commit()
    
    await interaction.response.send_message(f"✅ Removed {user.mention} from whitelist", ephemeral=False)

@bot.tree.command(name="blacklist", description="[ADMIN] Blacklist a user")
@app_commands.describe(user="User to blacklist", reason="Reason for blacklist")
async def blacklist(interaction: discord.Interaction, user: discord.User, reason: str = "No reason"):
    if not is_owner(interaction):
        return await interaction.response.send_message("❌ Owner only", ephemeral=True)
    
    c.execute("DELETE FROM users WHERE discord_id = ?", (str(user.id),))
    conn.commit()
    
    await interaction.response.send_message(f"✅ Blacklisted {user.mention}\nReason: {reason}", ephemeral=False)

@bot.tree.command(name="resethwid", description="[ADMIN] Reset user's HWID")
@app_commands.describe(user="User to reset")
async def resethwid(interaction: discord.Interaction, user: discord.User):
    if not is_owner(interaction):
        return await interaction.response.send_message("❌ Owner only", ephemeral=True)
    
    c.execute("UPDATE users SET hwid = NULL WHERE discord_id = ?", (str(user.id),))
    conn.commit()
    
    await interaction.response.send_message(f"✅ Reset HWID for {user.mention}", ephemeral=False)

@bot.tree.command(name="addproduct", description="[ADMIN] Add a product/script")
@app_commands.describe(product_id="Product ID", name="Product name", script_url="Script URL")
async def addproduct(interaction: discord.Interaction, product_id: str, name: str, script_url: str = None):
    if not is_owner(interaction):
        return await interaction.response.send_message("❌ Owner only", ephemeral=True)
    
    c.execute("INSERT OR REPLACE INTO products (id, name, script_url) VALUES (?, ?, ?)",
              (product_id, name, script_url))
    conn.commit()
    
    await interaction.response.send_message(f"✅ Added product: {name} ({product_id})", ephemeral=False)

@bot.tree.command(name="giveproduct", description="[ADMIN] Give a product to a user")
@app_commands.describe(user="User", product_id="Product ID")
async def giveproduct(interaction: discord.Interaction, user: discord.User, product_id: str):
    if not is_owner(interaction):
        return await interaction.response.send_message("❌ Owner only", ephemeral=True)
    
    c.execute("SELECT products FROM users WHERE discord_id = ?", (str(user.id),))
    result = c.fetchone()
    
    if result and result[0]:
        products = json.loads(result[0])
    else:
        products = []
    
    products.append(product_id)
    c.execute("UPDATE users SET products = ? WHERE discord_id = ?", (json.dumps(products), str(user.id)))
    conn.commit()
    
    await interaction.response.send_message(f"✅ Gave {product_id} to {user.mention}", ephemeral=False)

@bot.tree.command(name="removeproduct", description="[ADMIN] Remove product from user")
@app_commands.describe(user="User", product_id="Product ID")
async def removeproduct(interaction: discord.Interaction, user: discord.User, product_id: str):
    if not is_owner(interaction):
        return await interaction.response.send_message("❌ Owner only", ephemeral=True)
    
    c.execute("SELECT products FROM users WHERE discord_id = ?", (str(user.id),))
    result = c.fetchone()
    
    if result and result[0]:
        products = json.loads(result[0])
        if product_id in products:
            products.remove(product_id)
            c.execute("UPDATE users SET products = ? WHERE discord_id = ?", (json.dumps(products), str(user.id)))
            conn.commit()
    
    await interaction.response.send_message(f"✅ Removed {product_id} from {user.mention}", ephemeral=False)

@bot.tree.command(name="list", description="[ADMIN] List all whitelisted users")
async def list_users(interaction: discord.Interaction):
    if not is_owner(interaction):
        return await interaction.response.send_message("❌ Owner only", ephemeral=True)
    
    c.execute("SELECT discord_id, username, expires_at FROM users WHERE whitelisted = 1")
    users = c.fetchall()
    
    if not users:
        return await interaction.response.send_message("No whitelisted users", ephemeral=True)
    
    msg = "**📋 Whitelisted Users**\n\n"
    for uid, name, expires in users[:25]:
        expires_str = expires[:10] if expires else "Lifetime"
        msg += f"• {name} - Expires: {expires_str}\n"
    
    await interaction.response.send_message(msg, ephemeral=True)

@bot.command(name="verify")
async def verify_api(ctx, user_id: str, hwid: str = None):
    """API endpoint for Lua scripts to check whitelist status"""
    c.execute("SELECT * FROM users WHERE discord_id = ? AND whitelisted = 1", (user_id,))
    user = c.fetchone()
    
    if not user:
        return await ctx.send("NOT_WHITELISTED")
    
    if user[3]:
        expires = datetime.fromisoformat(user[3])
        if expires < datetime.now():
            return await ctx.send("EXPIRED")
    
    if hwid:
        c.execute("UPDATE users SET hwid = ? WHERE discord_id = ?", (hwid, user_id))
        conn.commit()
    
    await ctx.send("VERIFIED")

@bot.command(name="commands")
async def show_commands(ctx):
    await ctx.send("""
**🔐 Luarmor Whitelist Bot Commands**

**User Commands:**
`/redeem <key>` - Redeem a key to whitelist yourself
`/status` - Check your whitelist status

**Admin Commands (Owner only):**
`/genkey <days> [amount]` - Generate activation keys
`/whitelist <user> <days>` - Whitelist a user
`/unwhitelist <user>` - Remove user from whitelist
`/blacklist <user> [reason]` - Blacklist a user
`/resethwid <user>` - Reset user's HWID
`/addproduct <id> <name> [url]` - Add a product
`/giveproduct <user> <product_id>` - Give product to user
`/removeproduct <user> <product_id>` - Remove product
`/list` - List all whitelisted users
""")

if __name__ == "__main__":
    if not TOKEN:
        print("ERROR: DISCORD_TOKEN not set")
        exit(1)
    bot.run(TOKEN)

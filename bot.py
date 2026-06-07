import os
import discord
from discord.ext import commands
from discord.ui import Button, View
import random
import string
import base64
import zlib
import hashlib
import json

BOT_TOKEN = os.getenv('BOT_TOKEN')

if not BOT_TOKEN:
    print("❌ ERROR: BOT_TOKEN not set!")
    exit(1)

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
bot = commands.Bot(command_prefix='!', intents=intents)

# ============================================
# WHITELIST SYSTEM
# ============================================

WHITELIST_FILE = "whitelist.json"

def load_whitelist():
    try:
        with open(WHITELIST_FILE, 'r') as f:
            return json.load(f)
    except:
        return {}

def save_whitelist(whitelist):
    with open(WHITELIST_FILE, 'w') as f:
        json.dump(whitelist, f, indent=4)

whitelist = load_whitelist()

def is_whitelisted(user_id):
    return str(user_id) in whitelist

def add_to_whitelist(user_id, plan="premium"):
    whitelist[str(user_id)] = {
        "added": str(discord.utils.utcnow()),
        "plan": plan
    }
    save_whitelist(whitelist)

def remove_from_whitelist(user_id):
    if str(user_id) in whitelist:
        del whitelist[str(user_id)]
        save_whitelist(whitelist)

# ============================================
# MOONVEIL-STYLE OBFUSCATOR
# ============================================

class MoonveilObfuscator:
    
    @staticmethod
    def gen_rand(n=8):
        return ''.join(random.choices(string.ascii_letters + string.digits, k=n))
    
    @staticmethod
    def string_mangle(s):
        if len(s) == 0:
            return '""'
        
        # Multiple encoding methods
        method = random.randint(1, 4)
        
        if method == 1:
            # Character array
            chars = [f"string.char({ord(c)})" for c in s]
            return "(" + "..".join(chars) + ")"
        
        elif method == 2:
            # Base64 + hex
            encoded = base64.b64encode(s.encode()).decode()
            return f"(function() local t='{encoded}' local d='' for i=1,#t do d=d..string.char(string.byte(t,i)-{random.randint(1,5)}) end return d end)()"
        
        elif method == 3:
            # XOR cipher
            key = random.randint(1, 255)
            encrypted = ''.join(chr(ord(c) ^ key) for c in s)
            return f"(function() local k={key} local e='{encrypted}' local r='' for i=1,#e do r=r..string.char(string.byte(e,i)~=k) end return r end)()"
        
        else:
            # Reverse + decode
            reversed_s = s[::-1]
            return f"(string.reverse({MoonveilObfuscator.string_mangle(reversed_s)}))"
    
    @staticmethod
    def obfuscate(code, user_id):
        """Full obfuscation - only works for whitelisted user"""
        
        import re
        
        # Generate unique watermark for this user
        watermark = hashlib.md5(f"{user_id}{random.randint(1,999999)}".encode()).hexdigest()[:16]
        
        # Remove comments
        code = re.sub(r'--.*$', '', code, flags=re.MULTILINE)
        
        # Variable renaming
        keywords = {'if','then','else','end','function','local','return','for',
                    'while','do','nil','true','false','and','or','not','in',
                    'break','repeat','until','goto'}
        
        var_pool = [MoonveilObfuscator.gen_rand(12) for _ in range(200)]
        vars_found = set(re.findall(r'\b[a-zA-Z_][a-zA-Z0-9_]*\b', code))
        
        var_map = {}
        i = 0
        for var in vars_found:
            if var not in keywords and not var.startswith('__obf_'):
                var_map[var] = f"__obf_{var_pool[i % len(var_pool)]}"
                i += 1
        
        for old, new in var_map.items():
            code = re.sub(rf'\b{old}\b', new, code)
        
        # String encoding
        def encode_string(match):
            s = match.group(1)
            return MoonveilObfuscator.string_mangle(s)
        
        code = re.sub(r'"([^"]*)"', encode_string, code)
        code = re.sub(r"'([^']*)'", encode_string, code)
        
        # Number mangling
        def encode_number(match):
            num = int(match.group(0))
            operations = [
                f"({num})",
                f"(0x{hex(num)[2:]})",
                f"(#{string.ascii_letters[:num%52]})" if num < 52 else f"({num})",
                f"(string.byte('{random.choice(string.ascii_letters)}')-{random.randint(40, 120)})",
                f"({random.randint(1, num-1)}+{num-random.randint(1, num-1)})" if num > 2 else f"({num})"
            ]
            return random.choice(operations)
        
        code = re.sub(r'\b(\d+)\b', encode_number, code)
        
        # Compress
        compressed = base64.b64encode(zlib.compress(code.encode(), 9)).decode()
        
        # Whitelist check wrapper
        final = f"""
        -- Moonveil Protected Script
        -- User: {user_id}
        -- Hash: {watermark}
        
        (function()
            local _allowed = {str(user_id)}
            local _uid = tostring(owner and owner.ConsoleId or game:GetService("Players").LocalPlayer and game:GetService("Players").LocalPlayer.UserId or 0)
            
            if tostring(_uid) ~= tostring(_allowed) then
                local _msg = "⚠️ This script is locked to another user\\nContact @owner to purchase"
                if game:GetService("StarterGui"):FindFirstChild("SetCore") then
                    game:GetService("StarterGui"):SetCore("SendNotification", {{Title="Access Denied", Text=_msg, Duration=5}})
                end
                error("Unauthorized user: " .. _uid)
                return
            end
            
            local function _d(s)
                local _r = ""
                for _i=1,#s do
                    _r = _r .. string.char(string.byte(s,_i) - {random.randint(1, 15)})
                end
                return _r
            end
            
            local function _l(s)
                local _t = ""
                for _i=1,#s,2 do
                    _t = _t .. string.char(tonumber(s:sub(_i,_i+1), 16))
                end
                return _t
            end
            
            local _c = "{compressed}"
            local _x = _l(_d(_c))
            local _f = loadstring(_x)
            if _f then _f() end
        end)()
        """
        
        return final

# ============================================
# BUTTON PANEL
# ============================================

class WhitelistPanel(View):
    def __init__(self, user_id):
        super().__init__(timeout=None)
        self.user_id = user_id
    
    @discord.ui.button(label="🔒 Obfuscate Script", style=discord.ButtonStyle.primary, emoji="🔒")
    async def obfuscate_btn(self, interaction, button):
        if interaction.user.id != self.user_id:
            return await interaction.response.send_message("❌ Not your panel", ephemeral=True)
        
        if not is_whitelisted(self.user_id):
            return await interaction.response.send_message(
                "❌ **Access Denied**\nYou are not whitelisted to use this obfuscator.\nContact <@owner> to purchase access.",
                ephemeral=True
            )
        
        await interaction.response.send_message(
            "📤 **Send your .lua file or paste the code**\nYou have 60 seconds:",
            ephemeral=True
        )
        
        def check(m):
            return m.author.id == self.user_id and m.channel == interaction.channel
        
        try:
            msg = await bot.wait_for('message', timeout=60, check=check)
            
            if msg.attachments:
                data = await msg.attachments[0].read()
                code = data.decode('utf-8')
            else:
                code = msg.content
            
            if not code or len(code) < 10:
                return await interaction.followup.send("❌ Invalid code!", ephemeral=True)
            
            # Obfuscate
            result = MoonveilObfuscator.obfuscate(code, self.user_id)
            
            # Send result
            if len(result) < 1900:
                await interaction.followup.send(f"```lua\n{result}\n```", ephemeral=True)
            else:
                with open(f"obfuscated_{self.user_id}.lua", "w") as f:
                    f.write(result)
                await interaction.followup.send(
                    file=discord.File(f"obfuscated_{self.user_id}.lua"),
                    ephemeral=True
                )
                
        except Exception as e:
            await interaction.followup.send(f"❌ Error: {str(e)[:100]}", ephemeral=True)
    
    @discord.ui.button(label="📊 Check Status", style=discord.ButtonStyle.secondary, emoji="📊")
    async def status_btn(self, interaction, button):
        if interaction.user.id != self.user_id:
            return
        
        if is_whitelisted(self.user_id):
            plan = whitelist[str(self.user_id)].get("plan", "premium")
            await interaction.response.send_message(
                f"✅ **You are whitelisted!**\nPlan: `{plan}`\nUnlimited obfuscations",
                ephemeral=True
            )
        else:
            await interaction.response.send_message(
                "❌ **Not whitelisted**\nContact <@owner> to purchase access",
                ephemeral=True
            )

# ============================================
# ADMIN COMMANDS
# ============================================

@bot.command(name='adduser')
@commands.has_permissions(administrator=True)
async def add_user(ctx, user: discord.User, plan: str = "premium"):
    """Add user to whitelist: !adduser @user premium"""
    add_to_whitelist(user.id, plan)
    embed = discord.Embed(
        title="✅ User Whitelisted",
        description=f"{user.mention} has been added to whitelist",
        color=discord.Color.green()
    )
    embed.add_field(name="Plan", value=plan, inline=True)
    embed.add_field(name="User ID", value=user.id, inline=True)
    await ctx.send(embed=embed)

@bot.command(name='removeuser')
@commands.has_permissions(administrator=True)
async def remove_user(ctx, user: discord.User):
    """Remove user from whitelist: !removeuser @user"""
    remove_from_whitelist(user.id)
    await ctx.send(f"✅ {user.mention} removed from whitelist")

@bot.command(name='listusers')
@commands.has_permissions(administrator=True)
async def list_users(ctx):
    """List all whitelisted users"""
    if not whitelist:
        await ctx.send("No users in whitelist")
        return
    
    embed = discord.Embed(
        title="📋 Whitelisted Users",
        color=discord.Color.blue()
    )
    
    for uid, data in whitelist.items():
        user = await bot.fetch_user(int(uid))
        embed.add_field(
            name=user.name if user else uid,
            value=f"ID: `{uid}`\nPlan: {data.get('plan', 'premium')}",
            inline=False
        )
    
    await ctx.send(embed=embed)

# ============================================
# USER COMMANDS
# ============================================

@bot.command(name='panel')
async def panel(ctx):
    """Open obfuscator panel"""
    embed = discord.Embed(
        title="🔒 Moonveil Obfuscator",
        description="Protect your Lua scripts with military-grade encryption",
        color=discord.Color.purple()
    )
    embed.add_field("Features", "✓ User-locked scripts\n✓ Anti-tamper\n✓ String encoding\n✓ Variable renaming\n✓ Compression")
    embed.add_field("Price", "DM <@owner> for whitelist access", inline=False)
    
    view = WhitelistPanel(ctx.author.id)
    await ctx.send(embed=embed, view=view)

@bot.command(name='whitelist')
async def check_whitelist(ctx):
    """Check if you're whitelisted"""
    if is_whitelisted(ctx.author.id):
        plan = whitelist[str(ctx.author.id)].get("plan", "premium")
        await ctx.send(f"✅ You are whitelisted! Plan: `{plan}`")
    else:
        await ctx.send("❌ You are not whitelisted. Contact <@owner> to purchase access.")

# ============================================
# RUN BOT
# ============================================

@bot.event
async def on_ready():
    print(f"""
    ╔═══════════════════════════════════╗
    ║     MOONVEIL OBFUSCATOR BOT       ║
    ║     Whitelist mode: ACTIVE        ║
    ╚═══════════════════════════════════╝
    """)
    print(f"✅ Logged in as: {bot.user}")
    print(f"📋 Whitelisted users: {len(whitelist)}")
    print("=" * 40)

if __name__ == "__main__":
    bot.run(BOT_TOKEN)

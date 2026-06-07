import os
import discord
from discord.ext import commands
from discord.ui import Button, View
import random
import string
import re
import hashlib
import base64
import zlib

# ============================================
# READ TOKEN FROM RAILWAY ENVIRONMENT VARIABLE
# ============================================

BOT_TOKEN = os.getenv('BOT_TOKEN')

# Check if token exists
if not BOT_TOKEN:
    print("❌ ERROR: BOT_TOKEN not set in environment variables!")
    print("Go to Railway Dashboard → Variables → Add BOT_TOKEN")
    exit(1)

# ============================================
# BOT SETUP
# ============================================

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)

# ============================================
# ANTI-TAMPER OBFUSCATOR
# ============================================

class Obfuscator:
    
    @staticmethod
    def random_str(n=8):
        return ''.join(random.choices(string.ascii_letters, k=n))
    
    @staticmethod
    def obfuscate(code, level="hard"):
        
        # Remove comments
        code = re.sub(r'--.*$', '', code, flags=re.MULTILINE)
        
        # Rename variables
        keywords = {'if','then','else','end','function','local','return','for',
                    'while','do','nil','true','false','and','or','not','in'}
        
        vars_found = set(re.findall(r'\b[a-zA-Z_][a-zA-Z0-9_]*\b', code))
        var_map = {}
        for var in vars_found:
            if var not in keywords:
                var_map[var] = f'_{Obfuscator.random_str(10)}'
        
        for old, new in var_map.items():
            code = re.sub(rf'\b{old}\b', new, code)
        
        # Encode strings
        def encode(match):
            s = match.group(1)
            return '(' + '..'.join([f'string.char({ord(c)})' for c in s]) + ')'
        
        code = re.sub(r'"([^"]*)"', encode, code)
        code = re.sub(r"'([^']*)'", encode, code)
        
        # Anti-tamper checksum
        checksum = hashlib.md5(code.encode()).hexdigest()
        
        anti_tamper = f'''
        do
            local hash = "{checksum}"
            local original = [=[{code}]=]
            local function check(s)
                local h = 0
                for i=1,#s do h = (h * 31 + string.byte(s,i)) % 2^32 end
                return string.format("%x", h)
            end
            if check(original) ~= hash then
                error("Script integrity check failed")
            end
        end
        '''
        
        # Garbage code injection
        garbage = f'''
        do local x={random.randint(1,999)} for i=1,{random.randint(10,100)} do x=x+i end end
        do local _=function() return {random.randint(1,999)} end _() end
        '''
        
        # Final compression for hard level
        if level == "hard":
            compressed = base64.b64encode(zlib.compress((anti_tamper + garbage + code).encode())).decode()
            final = f'''
            loadstring((function(s)
                local d=base64.decode(s)
                local u=zlib.inflate(d)
                return u
            end)("{compressed}"))()
            '''
            return final
        else:
            return anti_tamper + garbage + code

# ============================================
# BUTTON PANEL
# ============================================

class ObfuscatePanel(View):
    def __init__(self, user_id):
        super().__init__(timeout=120)
        self.user_id = user_id
        self.level = "hard"
    
    @discord.ui.select(
        placeholder="Select protection level",
        options=[
            discord.SelectOption(label="Normal", value="normal", description="Basic protection"),
            discord.SelectOption(label="Hard", value="hard", description="Full protection + compression"),
        ]
    )
    async def select_level(self, interaction, select):
        if interaction.user.id != self.user_id:
            return await interaction.response.send_message("Not your panel", ephemeral=True)
        self.level = select.values[0]
        await interaction.response.send_message(f"✅ Level set to: {self.level}", ephemeral=True)
    
    @discord.ui.button(label="🔒 Obfuscate Script", style=discord.ButtonStyle.primary, emoji="🔒")
    async def obfuscate(self, interaction, button):
        if interaction.user.id != self.user_id:
            return await interaction.response.send_message("Not your panel", ephemeral=True)
        
        await interaction.response.send_message("📤 **Send your .lua file or paste the code**\nYou have 60 seconds:", ephemeral=True)
        
        def check(m):
            return m.author.id == self.user_id and m.channel == interaction.channel
        
        try:
            msg = await bot.wait_for('message', timeout=60, check=check)
            
            # Handle file upload
            if msg.attachments:
                file_data = await msg.attachments[0].read()
                code = file_data.decode('utf-8')
            else:
                code = msg.content
            
            if not code or len(code) < 5:
                return await interaction.followup.send("❌ No valid code received!", ephemeral=True)
            
            # Obfuscate
            result = Obfuscator.obfuscate(code, self.level)
            
            # Send result
            if len(result) < 1900:
                await interaction.followup.send(f"```lua\n{result}\n```", ephemeral=True)
            else:
                with open(f"obfuscated_{self.user_id}.lua", "w") as f:
                    f.write(result)
                await interaction.followup.send(file=discord.File(f"obfuscated_{self.user_id}.lua"), ephemeral=True)
                
        except Exception as e:
            await interaction.followup.send(f"❌ Error: {str(e)[:100]}", ephemeral=True)

# ============================================
# COMMANDS
# ============================================

@bot.event
async def on_ready():
    print(f"✅ {bot.user} is online!")
    print(f"📋 Bot is ready to obfuscate Lua scripts")
    print("=" * 40)

@bot.command(name='panel')
async def panel(ctx):
    """Open the obfuscator panel"""
    embed = discord.Embed(
        title="🔒 FLASH Obfuscator",
        description="Protect your Lua scripts from being stolen or reversed",
        color=discord.Color.blue()
    )
    embed.add_field(name="Features", value="✓ Anti-tamper checksum\n✓ Variable renaming\n✓ String encoding\n✓ Garbage injection\n✓ Compression", inline=False)
    embed.add_field(name="How to use", value="1. Select protection level\n2. Click Obfuscate\n3. Send your .lua file", inline=False)
    embed.set_footer(text="Your scripts are safe with us")
    
    view = ObfuscatePanel(ctx.author.id)
    await ctx.send(embed=embed, view=view)

@bot.command(name='obfuscate')
async def obfuscate(ctx):
    """Quick obfuscate command"""
    view = ObfuscatePanel(ctx.author.id)
    await ctx.send("Click the button to obfuscate your script", view=view)

# ============================================
# RUN BOT
# ============================================

if __name__ == "__main__":
    print("""
    ╔═══════════════════════════════╗
    ║     FLASH OBFUSCATOR BOT      ║
    ║     Ready to protect scripts  ║
    ╚═══════════════════════════════╝
    """)
    bot.run(BOT_TOKEN)

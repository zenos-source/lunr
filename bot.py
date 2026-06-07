import discord
from discord.ext import commands
from discord.ui import Button, View
import random
import string
import re
import hashlib
import base64
import zlib

BOT_TOKEN = "YOUR_BOT_TOKEN"

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
        
        # Step 1: Rename variables
        keywords = {'if','then','else','end','function','local','return','for',
                    'while','do','nil','true','false','and','or','not','in'}
        
        vars_found = set(re.findall(r'\b[a-zA-Z_][a-zA-Z0-9_]*\b', code))
        var_map = {}
        for var in vars_found:
            if var not in keywords:
                var_map[var] = f'_{Obfuscator.random_str(10)}'
        
        for old, new in var_map.items():
            code = re.sub(rf'\b{old}\b', new, code)
        
        # Step 2: Encode strings
        def encode(match):
            s = match.group(1)
            return '(' + '..'.join([f'string.char({ord(c)})' for c in s]) + ')'
        
        code = re.sub(r'"([^"]*)"', encode, code)
        code = re.sub(r"'([^']*)'", encode, code)
        
        # Step 3: Add anti-tamper
        checksum = hashlib.md5(code.encode()).hexdigest()
        
        anti_tamper = f'''
        -- ANTI-TAMPER
        do
            local hash = "{checksum}"
            local original = [=[{code}]=]
            local function check(s)
                local h = 0
                for i=1,#s do h = (h * 31 + string.byte(s,i)) % 2^32 end
                return string.format("%x", h)
            end
            if check(original) ~= hash then
                error("Invalid script")
            end
        end
        '''
        
        # Step 4: Add garbage code
        garbage = f'''
        do local x={random.randint(1,999)} for i=1,{random.randint(10,100)} do x=x+i end end
        do local _=function() return {random.randint(1,999)} end _() end
        '''
        
        # Step 5: Final wrapper
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
# BUTTONS
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
            discord.SelectOption(label="Hard (Recommended)", value="hard", description="Full protection + compression"),
        ]
    )
    async def select_level(self, interaction, select):
        if interaction.user.id != self.user_id:
            return await interaction.response.send_message("Not your panel", ephemeral=True)
        self.level = select.values[0]
        await interaction.response.send_message(f"✅ Level: {self.level}", ephemeral=True)
    
    @discord.ui.button(label="🔒 Obfuscate Script", style=discord.ButtonStyle.primary)
    async def obfuscate(self, interaction, button):
        if interaction.user.id != self.user_id:
            return
        
        await interaction.response.send_message("📤 **Send your .lua file**", ephemeral=True)
        
        def check(m):
            return m.author.id == self.user_id and m.channel == interaction.channel
        
        try:
            msg = await bot.wait_for('message', timeout=60, check=check)
            
            if msg.attachments:
                file = await msg.attachments[0].read()
                code = file.decode('utf-8')
            else:
                code = msg.content
            
            # Obfuscate
            result = Obfuscator.obfuscate(code, self.level)
            
            # Send result
            if len(result) < 1900:
                await interaction.followup.send(f"```lua\n{result}\n```", ephemeral=True)
            else:
                with open("output.lua", "w") as f:
                    f.write(result)
                await interaction.followup.send(file=discord.File("output.lua"), ephemeral=True)
                
        except Exception as e:
            await interaction.followup.send(f"❌ Error: {e}", ephemeral=True)

# ============================================
# COMMANDS
# ============================================

@bot.event
async def on_ready():
    print(f"✅ {bot.user} is online!")
    print("Commands: !panel, !obfuscate")

@bot.command()
async def panel(ctx):
    """Open obfuscator panel"""
    embed = discord.Embed(
        title="🔒 FLASH Obfuscator",
        description="Protect your Lua scripts from being stolen",
        color=discord.Color.blue()
    )
    embed.add_field("🔥 Features", "✓ Anti-tamper\n✓ String encoding\n✓ Variable renaming\n✓ Compression")
    
    await ctx.send(embed=embed, view=ObfuscatePanel(ctx.author.id))

@bot.command()
async def obfuscate(ctx):
    """Quick obfuscate"""
    view = ObfuscatePanel(ctx.author.id)
    await ctx.send("Click the button to obfuscate", view=view)

# ============================================
# RUN
# ============================================

if __name__ == "__main__":
    bot.run(BOT_TOKEN)

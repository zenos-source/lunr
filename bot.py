import os
import discord
from discord.ext import commands
import re
import base64
import zlib
import tempfile
import aiohttp

BOT_TOKEN = os.getenv('BOT_TOKEN')

if not BOT_TOKEN:
    print("❌ ERROR: BOT_TOKEN not set!")
    exit(1)

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix='.', intents=intents)

# ============================================
# LUNR DEOBFUSCATOR ENGINE
# ============================================

def process_script(content):
    """Main deobfuscation function"""
    
    # Extract from code block
    code_block = re.search(r'```(?:lua)?\n?([\s\S]*?)```', content)
    if code_block:
        script = code_block.group(1)
    else:
        script = content
    
    # Decode string.char chains
    def decode_chars(match):
        nums = re.findall(r'string\.char\((\d+)\)', match.group(0))
        if nums:
            return '"' + ''.join(chr(int(n)) for n in nums) + '"'
        return match.group(0)
    script = re.sub(r'(?:string\.char\(\d+\)(?:\.\.string\.char\(\d+\))*)', decode_chars, script)
    
    # Decode loadstring wrappers
    for match in re.findall(r'loadstring\(["\']([^"\']+)["\']\)\s*\(\s*\)', script):
        try:
            decoded = base64.b64decode(match).decode('utf-8')
            script = script.replace(f'loadstring("{match}")()', decoded)
        except:
            pass
    
    # Reverse string.reverse()
    script = re.sub(r'string\.reverse\(["\']([^"\']+)["\']\)', lambda m: '"' + m.group(1)[::-1] + '"', script)
    
    # Remove garbage
    garbage_patterns = [
        r'local _[a-zA-Z0-9]+ = {}\s*\n',
        r'do local x=\d+ for i=1,\d+ do x=x\+i end end\s*\n',
    ]
    for pattern in garbage_patterns:
        script = re.sub(pattern, '', script, flags=re.MULTILINE)
    
    return script.strip()

async def fetch_script(url):
    """Fetch script from URL"""
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            if response.status == 200:
                return await response.text()
            else:
                raise Exception(f"Failed to fetch: HTTP {response.status}")

# ============================================
# BOT COMMANDS
# ============================================

@bot.event
async def on_ready():
    print(f'✅ Logged in as {bot.user}')
    print('LUNR Deobfuscator Ready')
    print('Commands: .l, .get, .help')

@bot.command(name='l')
async def l_command(ctx, *, code: str = None):
    """Deobfuscate Lua code: .l ```lua code```"""
    
    script = None
    
    # Check for attachments
    if ctx.message.attachments:
        attachment = ctx.message.attachments[0]
        if attachment.filename.endswith('.lua'):
            data = await attachment.read()
            script = data.decode('utf-8')
    
    # Check for code block in message
    if not script and code:
        code_match = re.search(r'```(?:lua)?\n?([\s\S]*?)```', code)
        if code_match:
            script = code_match.group(1)
        else:
            script = code.strip()
    
    if not script:
        await ctx.send("❌ Provide .lua file or code block\n`.l ```lua print('hi')```")
        return
    
    await ctx.send("⏳ Processing...")
    
    try:
        result = process_script(script)
        
        if len(result) < 1900:
            await ctx.send(f"```lua\n{result}\n```")
        else:
            with tempfile.NamedTemporaryFile(mode='w', suffix='.lua', delete=False) as f:
                f.write(result)
                await ctx.send(file=discord.File(f.name))
            os.unlink(f.name)
    except Exception as e:
        await ctx.send(f"❌ Error: {e}")

@bot.command(name='get')
async def get_command(ctx, url: str = None):
    """Fetch and deobfuscate script from URL: .get https://pastebin.com/raw/xxx"""
    
    if not url:
        await ctx.send("❌ Usage: `.get https://pastebin.com/raw/xxx`")
        return
    
    await ctx.send(f"⏳ Fetching script from URL...")
    
    try:
        script = await fetch_script(url)
        
        if not script or len(script) < 10:
            await ctx.send("❌ Failed to fetch script or script is empty")
            return
        
        await ctx.send(f"⏳ Deobfuscating... (Fetched {len(script)} bytes)")
        
        result = process_script(script)
        
        if len(result) < 1900:
            await ctx.send(f"```lua\n{result}\n```")
        else:
            with tempfile.NamedTemporaryFile(mode='w', suffix='.lua', delete=False) as f:
                f.write(result)
                await ctx.send(file=discord.File(f.name))
            os.unlink(f.name)
            
    except Exception as e:
        await ctx.send(f"❌ Error: {e}")

@bot.command(name='help')
async def help_command(ctx):
    """Show all commands"""
    embed = discord.Embed(
        title="🔓 LUNR Deobfuscator",
        description="Deobfuscate Lua/Roblox scripts",
        color=discord.Color.blue()
    )
    embed.add_field(name=".l", value="Deobfuscate from code block or file\n`.l ```lua code``` `", inline=False)
    embed.add_field(name=".get", value="Fetch and deobfuscate from URL\n`.get https://pastebin.com/raw/xxx`", inline=False)
    embed.add_field(name=".help", value="Show this menu", inline=False)
    await ctx.send(embed=embed)

# ============================================
# RUN
# ============================================

if __name__ == "__main__":
    bot.run(BOT_TOKEN)

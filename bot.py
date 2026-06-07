import os
import discord
from discord.ext import commands
import re
import base64
import zlib
import aiohttp
import asyncio

BOT_TOKEN = os.getenv('BOT_TOKEN')

if not BOT_TOKEN:
    print("❌ ERROR: BOT_TOKEN not set!")
    exit(1)

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix='.', intents=intents)

# ============================================
# PURE PYTHON LUNR DEOBFUSCATOR
# ============================================

def clean_url(url):
    url = url.strip()
    url = re.sub(r'[)\'"]+$', '', url)
    url = re.sub(r'^[\'"]+', '', url)
    return url

def decode_string_chars(code):
    """Convert string.char(104)..string.char(101) to text"""
    def replace(match):
        nums = re.findall(r'string\.char\((\d+)\)', match.group(0))
        if nums:
            return '"' + ''.join(chr(int(n)) for n in nums) + '"'
        return match.group(0)
    return re.sub(r'(?:string\.char\(\d+\)(?:\.\.string\.char\(\d+\))*)', replace, code)

def decode_loadstring(code):
    """Extract and decode loadstring wrappers"""
    for match in re.findall(r'loadstring\(["\']([^"\']+)["\']\)\s*\(\s*\)', code):
        try:
            decoded = base64.b64decode(match).decode('utf-8')
            code = code.replace(f'loadstring("{match}")()', decoded)
            code = code.replace(f"loadstring('{match}')()", decoded)
        except:
            pass
    return code

def decode_hex(code):
    """Decode hex strings like \x48\x65\x6c\x6c\x6f"""
    def replace(match):
        hex_str = match.group(0)
        try:
            hex_bytes = re.findall(r'\\x([0-9a-fA-F]{2})', hex_str)
            if hex_bytes:
                return '"' + ''.join(chr(int(h, 16)) for h in hex_bytes) + '"'
        except:
            pass
        return hex_str
    return re.sub(r'(?:\\x[0-9a-fA-F]{2})+', replace, code)

def reverse_strings(code):
    """Convert string.reverse('text') back to normal"""
    return re.sub(r'string\.reverse\(["\']([^"\']+)["\']\)', lambda m: '"' + m.group(1)[::-1] + '"', code)

def remove_garbage(code):
    """Remove junk code"""
    lines = code.split('\n')
    cleaned = []
    skip = False
    
    for line in lines:
        if 'if (true or false)' in line or 'if (1 + 1 == 2)' in line:
            if 'then' in line:
                skip = True
            continue
        if skip and 'end' in line:
            skip = False
            continue
        if skip:
            continue
        if re.match(r'local _[a-zA-Z0-9]+ = {}\s*$', line):
            continue
        if re.match(r'for _[a-zA-Z0-9]+ = 1, \d+ do', line):
            continue
        cleaned.append(line)
    
    return '\n'.join(cleaned)

def deobfuscate(script):
    """Main deobfuscation pipeline"""
    result = script
    result = decode_loadstring(result)
    result = decode_string_chars(result)
    result = decode_hex(result)
    result = reverse_strings(result)
    result = remove_garbage(result)
    
    # Clean up multiple newlines
    result = re.sub(r'\n\s*\n', '\n', result)
    
    return result.strip()

async def fetch_script(url):
    """Fetch script from URL with timeout"""
    url = clean_url(url)
    timeout = aiohttp.ClientTimeout(total=30)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        async with session.get(url) as response:
            if response.status == 200:
                return await response.text()
            else:
                raise Exception(f"HTTP {response.status}")

# ============================================
# BOT COMMANDS
# ============================================

@bot.event
async def on_ready():
    print(f'✅ LUNR Ready - {bot.user}')
    print('Pure Python - No Lua required')

@bot.command(name='l')
async def l_command(ctx, *, code: str = None):
    """Deobfuscate Lua code"""
    
    script = None
    
    if ctx.message.attachments:
        attachment = ctx.message.attachments[0]
        if attachment.filename.endswith('.lua'):
            data = await attachment.read()
            script = data.decode('utf-8')
    
    if not script and code:
        code_match = re.search(r'```(?:lua)?\n?([\s\S]*?)```', code)
        if code_match:
            script = code_match.group(1)
        elif code.strip():
            script = code.strip()
    
    if not script:
        await ctx.send("❌ No code found.\nUsage: `.l ```lua code``` or attach .lua file")
        return
    
    msg = await ctx.send("🔓 Deobfuscating...")
    
    try:
        result = await asyncio.to_thread(deobfuscate, script)
        
        if not result or len(result) < 10:
            await msg.edit(content="❌ Nothing to output - script may already be clean")
            return
        
        if len(result) < 1900:
            await msg.edit(content=f"```lua\n{result}\n```")
        else:
            import tempfile
            with tempfile.NamedTemporaryFile(mode='w', suffix='.lua', delete=False) as f:
                f.write(result)
                await ctx.send(file=discord.File(f.name, filename="deobfuscated.lua"))
                os.unlink(f.name)
            await msg.delete()
            
    except Exception as e:
        await msg.edit(content=f"❌ Error: {str(e)[:200]}")

@bot.command(name='get')
async def get_command(ctx, *, url: str = None):
    """Fetch and deobfuscate from URL"""
    
    if not url:
        await ctx.send("❌ Usage: `.get https://pastebin.com/raw/xxx`")
        return
    
    clean = clean_url(url)
    msg = await ctx.send(f"📥 Fetching from URL...")
    
    try:
        script = await fetch_script(clean)
        
        if not script or len(script) < 10:
            await msg.edit(content=f"❌ Failed to fetch from `{clean}`")
            return
        
        await msg.edit(content=f"🔓 Deobfuscating... ({len(script)} bytes)")
        
        result = await asyncio.to_thread(deobfuscate, script)
        
        if not result or len(result) < 10:
            await msg.edit(content="❌ Deobfuscation produced no output")
            return
        
        if len(result) < 1900:
            await msg.edit(content=f"```lua\n{result}\n```")
        else:
            import tempfile
            with tempfile.NamedTemporaryFile(mode='w', suffix='.lua', delete=False) as f:
                f.write(result)
                await ctx.send(file=discord.File(f.name, filename="deobfuscated.lua"))
                os.unlink(f.name)
            await msg.delete()
            
    except asyncio.TimeoutError:
        await msg.edit(content="❌ Request timed out")
    except Exception as e:
        await msg.edit(content=f"❌ Error: {str(e)[:200]}")

@bot.command(name='help')
async def help_cmd(ctx):
    embed = discord.Embed(
        title="🔓 LUNR Deobfuscator",
        description="Deobfuscate Lua/Roblox scripts - Pure Python",
        color=discord.Color.blue()
    )
    embed.add_field(name=".l", value="Deobfuscate from code block or .lua file", inline=False)
    embed.add_field(name=".get", value="Fetch and deobfuscate from URL\n`.get https://pastebin.com/raw/xxx`", inline=False)
    await ctx.send(embed=embed)

# ============================================
# RUN
# ============================================

if __name__ == "__main__":
    bot.run(BOT_TOKEN)

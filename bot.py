import os
import discord
from discord.ext import commands
import re
import base64
import aiohttp
import asyncio
import tempfile

BOT_TOKEN = os.getenv('BOT_TOKEN')

if not BOT_TOKEN:
    print("❌ ERROR: BOT_TOKEN not set!")
    exit(1)

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix='.', intents=intents)

# ============================================
# LUNR DEOBFUSCATOR
# ============================================

def clean_url(url):
    url = url.strip()
    url = re.sub(r'[)\'"]+$', '', url)
    url = re.sub(r'^[\'"]+', '', url)
    return url

def deobfuscate(script):
    # Decode loadstring
    for match in re.findall(r'loadstring\(["\']([^"\']+)["\']\)\s*\(\s*\)', script):
        try:
            decoded = base64.b64decode(match).decode('utf-8')
            script = script.replace(f'loadstring("{match}")()', decoded)
        except:
            pass
    
    # Decode string.char
    def decode_chars(m):
        nums = re.findall(r'string\.char\((\d+)\)', m.group(0))
        if nums:
            return '"' + ''.join(chr(int(n)) for n in nums) + '"'
        return m.group(0)
    script = re.sub(r'(?:string\.char\(\d+\)(?:\.\.string\.char\(\d+\))*)', decode_chars, script)
    
    # Reverse string.reverse
    script = re.sub(r'string\.reverse\(["\']([^"\']+)["\']\)', lambda m: '"' + m.group(1)[::-1] + '"', script)
    
    # Remove garbage
    lines = script.split('\n')
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
        cleaned.append(line)
    
    return '\n'.join(cleaned).strip()

async def fetch_script(url):
    url = clean_url(url)
    timeout = aiohttp.ClientTimeout(total=30)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        async with session.get(url) as response:
            if response.status == 200:
                return await response.text()
            raise Exception(f"HTTP {response.status}")

# ============================================
# COMMANDS
# ============================================

@bot.event
async def on_ready():
    print(f'✅ LUNR Ready - {bot.user}')
    print('Commands: .l , .get')

@bot.command(name='l')
async def l_cmd(ctx, *, code: str = None):
    script = None
    
    if ctx.message.attachments:
        attachment = ctx.message.attachments[0]
        if attachment.filename.endswith('.lua'):
            data = await attachment.read()
            script = data.decode('utf-8')
    
    if not script and code:
        match = re.search(r'```(?:lua)?\n?([\s\S]*?)```', code)
        if match:
            script = match.group(1)
        elif code.strip():
            script = code.strip()
    
    if not script:
        await ctx.send("❌ Usage: `.l ```lua code``` or attach .lua file")
        return
    
    msg = await ctx.send("🔓 Processing...")
    
    try:
        result = await asyncio.to_thread(deobfuscate, script)
        
        if not result or len(result) < 10:
            await msg.edit(content="❌ No output")
            return
        
        if len(result) < 1900:
            await msg.edit(content=f"```lua\n{result}\n```")
        else:
            with tempfile.NamedTemporaryFile(mode='w', suffix='.lua', delete=False) as f:
                f.write(result)
                await ctx.send(file=discord.File(f.name, filename="deobfuscated.lua"))
                os.unlink(f.name)
            await msg.delete()
    except Exception as e:
        await msg.edit(content=f"❌ Error: {str(e)[:200]}")

@bot.command(name='get')
async def get_cmd(ctx, *, url: str = None):
    if not url:
        await ctx.send("❌ Usage: `.get https://pastebin.com/raw/xxx`")
        return
    
    msg = await ctx.send("📥 Fetching...")
    
    try:
        script = await fetch_script(url)
        
        if not script or len(script) < 10:
            await msg.edit(content="❌ Failed to fetch")
            return
        
        await msg.edit(content="🔓 Deobfuscating...")
        result = await asyncio.to_thread(deobfuscate, script)
        
        if not result or len(result) < 10:
            await msg.edit(content="❌ No output")
            return
        
        if len(result) < 1900:
            await msg.edit(content=f"```lua\n{result}\n```")
        else:
            with tempfile.NamedTemporaryFile(mode='w', suffix='.lua', delete=False) as f:
                f.write(result)
                await ctx.send(file=discord.File(f.name, filename="deobfuscated.lua"))
                os.unlink(f.name)
            await msg.delete()
    except Exception as e:
        await msg.edit(content=f"❌ Error: {str(e)[:200]}")

# ============================================
# RUN
# ============================================

if __name__ == "__main__":
    bot.run(BOT_TOKEN)

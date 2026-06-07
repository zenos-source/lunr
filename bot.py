import os
import discord
from discord.ext import commands
import re
import base64
import tempfile
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
# LUNR DEOBFUSCATOR ENGINE
# ============================================

def clean_url(url):
    """Clean URL from extra characters"""
    url = url.strip()
    url = re.sub(r'[)\'"]+$', '', url)
    url = re.sub(r'^[\'"]+', '', url)
    return url

def process_script(content):
    """Main deobfuscation function"""
    
    script = content
    
    # Decode string.char chains
    def decode_chars(match):
        nums = re.findall(r'string\.char\((\d+)\)', match.group(0))
        if nums:
            return '"' + ''.join(chr(int(n)) for n in nums) + '"'
        return match.group(0)
    
    try:
        script = re.sub(r'(?:string\.char\(\d+\)(?:\.\.string\.char\(\d+\))*)', decode_chars, script)
    except:
        pass
    
    # Decode loadstring wrappers
    for match in re.findall(r'loadstring\(["\']([^"\']+)["\']\)\s*\(\s*\)', script):
        try:
            decoded = base64.b64decode(match).decode('utf-8')
            script = script.replace(f'loadstring("{match}")()', decoded)
            script = script.replace(f"loadstring('{match}')()", decoded)
        except:
            pass
    
    # Reverse string.reverse()
    try:
        script = re.sub(r'string\.reverse\(["\']([^"\']+)["\']\)', lambda m: '"' + m.group(1)[::-1] + '"', script)
    except:
        pass
    
    return script.strip()

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
    print('Commands: .l , .get')

@bot.command(name='l')
async def l_command(ctx, *, code: str = None):
    """Deobfuscate Lua code"""
    
    script = None
    
    # Check attachments
    if ctx.message.attachments:
        attachment = ctx.message.attachments[0]
        if attachment.filename.endswith('.lua'):
            data = await attachment.read()
            script = data.decode('utf-8')
    
    # Check for code block
    if not script and code:
        code_match = re.search(r'```(?:lua)?\n?([\s\S]*?)```', code)
        if code_match:
            script = code_match.group(1)
        elif code.strip():
            script = code.strip()
    
    if not script:
        await ctx.send("❌ No code found.\nUsage: `.l \\`\\`\\`lua code\\`\\`\\`` or attach .lua file")
        return
    
    async with ctx.typing():
        try:
            result = await asyncio.to_thread(process_script, script)
            
            if not result or len(result) < 10:
                await ctx.send("❌ Nothing to output - script may already be clean")
                return
            
            # Send as file
            with tempfile.NamedTemporaryFile(mode='w', suffix='.lua', delete=False) as f:
                f.write(result)
                f.flush()
                await ctx.send(file=discord.File(f.name, filename="deobfuscated.lua"))
            os.unlink(f.name)
            
        except Exception as e:
            await ctx.send(f"❌ Error: {str(e)[:200]}")

@bot.command(name='get')
async def get_command(ctx, *, url: str = None):
    """Fetch and deobfuscate from URL"""
    
    if not url:
        await ctx.send("❌ Usage: `.get https://pastebin.com/raw/xxx`")
        return
    
    clean_url_str = clean_url(url)
    
    async with ctx.typing():
        try:
            script = await fetch_script(clean_url_str)
            
            if not script or len(script) < 10:
                await ctx.send(f"❌ Failed to fetch from `{clean_url_str}`")
                return
            
            result = await asyncio.to_thread(process_script, script)
            
            if not result or len(result) < 10:
                await ctx.send("❌ Deobfuscation produced no output")
                return
            
            # Send as file
            with tempfile.NamedTemporaryFile(mode='w', suffix='.lua', delete=False) as f:
                f.write(result)
                f.flush()
                await ctx.send(file=discord.File(f.name, filename="deobfuscated.lua"))
            os.unlink(f.name)
            
        except aiohttp.ClientError as e:
            await ctx.send(f"❌ Network error: {str(e)[:100]}")
        except Exception as e:
            await ctx.send(f"❌ Error: {str(e)[:200]}")

# ============================================
# RUN
# ============================================

if __name__ == "__main__":
    bot.run(BOT_TOKEN)

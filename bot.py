import os
import discord
from discord.ext import commands
import re
import base64
import aiohttp
import asyncio
import tempfile
import lupa
from lupa import LuaRuntime

BOT_TOKEN = os.getenv('BOT_TOKEN')

if not BOT_TOKEN:
    print("❌ ERROR: BOT_TOKEN not set!")
    exit(1)

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix='.', intents=intents)

# ============================================
# XOR DECRYPTION ENGINE
# ============================================

def clean_url(url):
    url = url.strip()
    url = re.sub(r'[)\'"]+$', '', url)
    url = re.sub(r'^[\'"]+', '', url)
    return url

def extract_xor_keys(script):
    """Extract XOR keys from the obfuscated script"""
    keys = []
    
    # Pattern for XOR decryption function
    xor_pattern = r'function\(([^,]+),([^)]+)\)local _[^=]+=""for _[^=]+=1,#\1 do _[^=]+=_[^=]+\.\.string\.char\(\1\[_[^=]+\]~\(\(\(\2\+_[^=]+-1\)%255\)\+1\)\)end return _[^=]+'
    
    # Find all XOR functions
    matches = re.findall(xor_pattern, script)
    
    for match in matches:
        key_var = match[1].strip()
        # Try to extract the key value
        key_match = re.search(rf'{key_var}\s*=\s*(\d+)', script)
        if key_match:
            keys.append(int(key_match.group(1)))
    
    return keys

def xor_decrypt(data, key):
    """XOR decryption"""
    result = []
    for i, char in enumerate(data):
        shift = (key + i) % 255 + 1
        result.append(chr(ord(char) ^ shift))
    return ''.join(result)

def deobfuscate(script):
    """Deobfuscate XOR-encrypted scripts"""
    
    result = script
    
    # 1. Extract and decrypt XOR strings
    xor_pattern = r'(function\([^,]+,[^)]+\)local _[^=]+=""for _[^=]+=1,#\1 do _[^=]+=_[^=]+\.\.string\.char\(\1\[_[^=]+\]~\(\(\(\2\+_[^=]+-1\)%255\)\+1\)\)end return _[^=]+)\(([^,]+),(\d+)\)'
    
    for match in re.findall(xor_pattern, result):
        func, encrypted_str, key = match
        try:
            # Extract the encrypted data
            encrypted_match = re.search(rf'{func}\(([^,]+),{key}\)', result)
            if encrypted_match:
                encrypted = encrypted_match.group(1).strip('"\'')
                decrypted = xor_decrypt(encrypted, int(key))
                result = result.replace(match[0], f'"{decrypted}"')
        except:
            pass
    
    # 2. Decode loadstring
    loadstring_pattern = r'loadstring\(["\']([^"\']+)["\']\)\s*\(\s*\)'
    for match in re.findall(loadstring_pattern, result):
        try:
            decoded = base64.b64decode(match).decode('utf-8')
            result = result.replace(f'loadstring("{match}")()', decoded)
        except:
            pass
    
    # 3. Decode string.char chains
    def decode_chars(m):
        nums = re.findall(r'string\.char\((\d+)\)', m.group(0))
        if nums:
            return '"' + ''.join(chr(int(n)) for n in nums) + '"'
        return m.group(0)
    result = re.sub(r'(?:string\.char\(\d+\)(?:\.\.string\.char\(\d+\))*)', decode_chars, result)
    
    # 4. Remove garbage code
    lines = result.split('\n')
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
        if re.match(r'for _[a-zA-Z0-9]+ = 1, \d+ do _[a-zA-Z0-9]+ = _[a-zA-Z0-9]+ [*+-] \d+ end\s*$', line):
            continue
        cleaned.append(line)
    
    result = '\n'.join(cleaned)
    result = re.sub(r'\n\s*\n', '\n', result)
    
    return result.strip()

async def fetch_script(url):
    url = clean_url(url)
    timeout = aiohttp.ClientTimeout(total=30)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        async with session.get(url) as response:
            if response.status == 200:
                return await response.text()
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
    """Deobfuscate Lua code (handles XOR encryption)"""
    
    script = None
    
    if ctx.message.attachments:
        attachment = ctx.message.attachments[0]
        if attachment.filename.endswith(('.lua', '.txt')):
            data = await attachment.read()
            script = data.decode('utf-8')
    
    if not script and code:
        if code.startswith(('http://', 'https://')):
            msg = await ctx.send("📥 Fetching from URL...")
            try:
                script = await fetch_script(code)
                await msg.edit(content="🔓 Deobfuscating...")
            except Exception as e:
                await msg.edit(content=f"❌ Failed to fetch: {str(e)[:100]}")
                return
        else:
            match = re.search(r'```(?:lua)?\n?([\s\S]*?)```', code)
            if match:
                script = match.group(1)
            elif code.strip():
                script = code.strip()
    
    if not script:
        await ctx.send("❌ Usage:\n`.l https://example.com/script.lua`\n`.l ```lua code``` `\n`.l` + attach .lua/.txt file")
        return
    
    if 'msg' not in locals():
        msg = await ctx.send("🔓 Deobfuscating...")
    
    try:
        result = await asyncio.to_thread(deobfuscate, script)
        
        if not result or len(result) < 10:
            await msg.edit(content="❌ No output - script may already be clean")
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
async def get_command(ctx, *, url: str = None):
    """Fetch script from URL (no deobfuscation)"""
    
    if not url:
        await ctx.send("❌ Usage: `.get https://pastebin.com/raw/xxx`")
        return
    
    msg = await ctx.send("📥 Fetching...")
    
    try:
        script = await fetch_script(url)
        
        if not script or len(script) < 10:
            await msg.edit(content="❌ Failed to fetch script")
            return
        
        if len(script) < 1900:
            await msg.edit(content=f"```lua\n{script}\n```")
        else:
            with tempfile.NamedTemporaryFile(mode='w', suffix='.lua', delete=False) as f:
                f.write(script)
                await ctx.send(file=discord.File(f.name, filename="fetched.lua"))
                os.unlink(f.name)
            await msg.delete()
            
    except asyncio.TimeoutError:
        await msg.edit(content="❌ Request timed out")
    except Exception as e:
        await msg.edit(content=f"❌ Error: {str(e)[:200]}")

# ============================================
# RUN
# ============================================

if __name__ == "__main__":
    bot.run(BOT_TOKEN)

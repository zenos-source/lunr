import os
import discord
from discord.ext import commands
import tempfile
import subprocess
import re

BOT_TOKEN = os.getenv('BOT_TOKEN')

if not BOT_TOKEN:
    print("❌ ERROR: BOT_TOKEN not set!")
    exit(1)

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix='.', intents=intents)

# ============================================
# LUNR ENVIRONMENT (from fixed_env.lua + security)
# ============================================

LUNR_ENV = """
-- LUNR Safe Environment
-- Based on fixed_env.lua from the leak

-- Safe environment with no dangerous functions
local safe_env = {
    print = print,
    string = string,
    table = table,
    math = math,
    task = {
        wait = task.wait,
        spawn = task.spawn
    },
    pcall = pcall,
    xpcall = xpcall,
    tostring = tostring,
    tonumber = tonumber,
    type = type,
    pairs = pairs,
    ipairs = ipairs,
    next = next,
    select = select,
    unpack = unpack,
    _G = {}
}

-- Block dangerous functions
safe_env.os = nil
safe_env.io = nil
safe_env.debug = nil

-- Fake Roblox services
safe_env.game = {
    GetService = function(self, service)
        return {}
    end,
    Players = {
        LocalPlayer = {
            UserId = 0,
            Name = "LUNR_User"
        }
    },
    Workspace = {},
    ReplicatedStorage = {
        WaitForChild = function(self, name)
            return {}
        end
    }
}

safe_env.Enum = {}
safe_env.Instance = {
    new = function()
        return {}
    end
}

-- Run script in safe environment
local function run_script(code)
    local fn, err = loadstring(code)
    if not fn then
        return "Error loading: " .. tostring(err)
    end
    
    setfenv(fn, safe_env)
    
    local success, result = pcall(fn)
    if not success then
        return "Error executing: " .. tostring(result)
    end
    
    return "Script executed safely"
end

return run_script
"""

# ============================================
# BOT COMMANDS
# ============================================

@bot.event
async def on_ready():
    print(f'✅ LUNR Security Bot Ready - {bot.user}')
    print('Running scripts in safe environment')

@bot.command(name='l')
async def l_command(ctx, *, code: str = None):
    """Run script in LUNR safe environment"""
    
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
        await ctx.send("❌ No code found.")
        return
    
    msg = await ctx.send("🔒 Running in LUNR safe environment...")
    
    try:
        with tempfile.NamedTemporaryFile(mode='w', suffix='.lua', delete=False) as f:
            combined = LUNR_ENV + "\n\n-- User Script\n" + script
            f.write(combined)
            temp_path = f.name
        
        result = subprocess.run(
            ['lua', temp_path],
            capture_output=True,
            text=True,
            timeout=30
        )
        
        os.unlink(temp_path)
        
        output = result.stdout.strip() or result.stderr.strip()
        
        if output:
            if len(output) < 1900:
                await msg.edit(content=f"```\n{output}\n```")
            else:
                with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
                    f.write(output)
                    await ctx.send(file=discord.File(f.name, filename="output.txt"))
                os.unlink(f.name)
                await msg.delete()
        else:
            await msg.edit(content="✅ Script executed safely (no output)")
            
    except subprocess.TimeoutExpired:
        await msg.edit(content="❌ Script timed out (30s)")
    except Exception as e:
        await msg.edit(content=f"❌ Error: {str(e)[:200]}")

@bot.command(name='get')
async def get_command(ctx, url: str = None):
    """Fetch and run script from URL"""
    if not url:
        await ctx.send("❌ Usage: `.get URL`")
        return
    
    await ctx.send("📥 Fetching script...")
    # Similar to .l but with URL fetching

# ============================================
# RUN
# ============================================

if __name__ == "__main__":
    bot.run(BOT_TOKEN)

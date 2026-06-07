const { Client, GatewayIntentBits, Partials, AttachmentBuilder } = require('discord.js');
const fs = require('fs');
const path = require('path');
const { exec } = require('child_process');
const util = require('util');
const execPromise = util.promisify(exec);
const axios = require('axios');

const client = new Client({
    intents: [
        GatewayIntentBits.Guilds,
        GatewayIntentBits.GuildMessages,
        GatewayIntentBits.MessageContent,
        GatewayIntentBits.DirectMessages,
    ],
    partials: [Partials.Channel]
});

const BOT_TOKEN = process.env.BOT_TOKEN;

if (!BOT_TOKEN) {
    console.error('❌ BOT_TOKEN not set!');
    process.exit(1);
}

// Create temp directory for processing
const TEMP_DIR = path.join(__dirname, 'temp');
if (!fs.existsSync(TEMP_DIR)) fs.mkdirSync(TEMP_DIR);

function cleanUrl(url) {
    url = url.trim();
    url = url.replace(/[)\'"]+$/, '');
    url = url.replace(/^[\'"]+/, '');
    return url;
}

async function deobfuscateWithPrometheus(script, preset = 'medium') {
    // Create temp input file
    const inputFile = path.join(TEMP_DIR, `input_${Date.now()}.lua`);
    const outputFile = path.join(TEMP_DIR, `output_${Date.now()}.lua`);
    
    fs.writeFileSync(inputFile, script);
    
    try {
        // Run Prometheus CLI
        const { stdout, stderr } = await execPromise(
            `lua Prometheus/cli.lua --p ${preset} --o ${outputFile} ${inputFile}`,
            { timeout: 30000 }
        );
        
        if (fs.existsSync(outputFile)) {
            const result = fs.readFileSync(outputFile, 'utf8');
            return result;
        }
        
        // Fallback to simple deobf
        return simpleDeobfuscate(script);
    } catch (error) {
        console.error('Prometheus error:', error.message);
        return simpleDeobfuscate(script);
    } finally {
        // Cleanup
        try { fs.unlinkSync(inputFile); } catch(e) {}
        try { fs.unlinkSync(outputFile); } catch(e) {}
    }
}

function simpleDeobfuscate(script) {
    let result = script;
    
    // Decode loadstring
    const loadstringMatches = result.match(/loadstring\(["']([^"']+)["']\)\s*\(\s*\)/g);
    if (loadstringMatches) {
        for (const match of loadstringMatches) {
            const encoded = match.match(/loadstring\(["']([^"']+)["']\)/);
            if (encoded && encoded[1]) {
                try {
                    const decoded = Buffer.from(encoded[1], 'base64').toString('utf8');
                    result = result.replace(match, decoded);
                } catch(e) {}
            }
        }
    }
    
    // Decode string.char chains
    result = result.replace(/(?:string\.char\(\d+\)(?:\.\.string\.char\(\d+\))*)/g, (match) => {
        const nums = match.match(/string\.char\((\d+)\)/g);
        if (nums) {
            let str = '';
            for (const num of nums) {
                const n = parseInt(num.match(/\d+/)[0]);
                str += String.fromCharCode(n);
            }
            return '"' + str + '"';
        }
        return match;
    });
    
    // Reverse string.reverse
    result = result.replace(/string\.reverse\(["']([^"']+)["']\)/g, (_, str) => {
        return '"' + str.split('').reverse().join('') + '"';
    });
    
    // Remove garbage
    const lines = result.split('\n');
    const cleaned = [];
    let skip = false;
    
    for (const line of lines) {
        if (line.includes('if (true or false)') || line.includes('if (1 + 1 == 2)')) {
            if (line.includes('then')) skip = true;
            continue;
        }
        if (skip && line.includes('end')) {
            skip = false;
            continue;
        }
        if (skip) continue;
        cleaned.push(line);
    }
    
    return cleaned.join('\n');
}

async function fetchScript(url) {
    const clean = cleanUrl(url);
    const response = await axios.get(clean, { timeout: 30000 });
    return response.data;
}

client.once('ready', () => {
    console.log(`✅ LUNR Ready - ${client.user.tag}`);
    console.log('Commands: .l , .get');
});

client.on('messageCreate', async (message) => {
    if (message.author.bot) return;
    if (!message.content.startsWith('.')) return;
    
    const args = message.content.slice(1).trim().split(/\s+/);
    const command = args[0].toLowerCase();
    
    if (command === 'l') {
        let script = null;
        
        // Check attachments
        if (message.attachments.size > 0) {
            const attachment = message.attachments.first();
            if (attachment.name.endsWith('.lua')) {
                const response = await axios.get(attachment.url);
                script = response.data;
            }
        }
        
        // Check code block
        if (!script && args.length > 1) {
            const code = args.slice(1).join(' ');
            const codeMatch = code.match(/```(?:lua)?\n?([\s\S]*?)```/);
            if (codeMatch) {
                script = codeMatch[1];
            } else {
                script = code;
            }
        }
        
        if (!script) {
            await message.reply('❌ No code found. Use `.l \\`\\`\\`lua code\\`\\`\\`` or attach .lua file');
            return;
        }
        
        const statusMsg = await message.reply('🔓 Deobfuscating...');
        
        try {
            const result = await deobfuscateWithPrometheus(script);
            
            if (!result || result.length < 10) {
                await statusMsg.edit('❌ No output');
                return;
            }
            
            if (result.length < 1900) {
                await statusMsg.edit(`\`\`\`lua\n${result}\n\`\`\``);
            } else {
                const outputFile = path.join(TEMP_DIR, `result_${Date.now()}.lua`);
                fs.writeFileSync(outputFile, result);
                await message.reply({
                    files: [new AttachmentBuilder(outputFile, { name: 'deobfuscated.lua' })]
                });
                fs.unlinkSync(outputFile);
                await statusMsg.delete();
            }
        } catch (error) {
            await statusMsg.edit(`❌ Error: ${error.message.slice(0, 200)}`);
        }
    }
    
    else if (command === 'get') {
        const url = args[1];
        if (!url) {
            await message.reply('❌ Usage: `.get https://pastebin.com/raw/xxx`');
            return;
        }
        
        const statusMsg = await message.reply('📥 Fetching...');
        
        try {
            const script = await fetchScript(url);
            
            if (!script || script.length < 10) {
                await statusMsg.edit('❌ Failed to fetch');
                return;
            }
            
            await statusMsg.edit('🔓 Deobfuscating...');
            const result = await deobfuscateWithPrometheus(script);
            
            if (!result || result.length < 10) {
                await statusMsg.edit('❌ No output');
                return;
            }
            
            if (result.length < 1900) {
                await statusMsg.edit(`\`\`\`lua\n${result}\n\`\`\``);
            } else {
                const outputFile = path.join(TEMP_DIR, `result_${Date.now()}.lua`);
                fs.writeFileSync(outputFile, result);
                await message.reply({
                    files: [new AttachmentBuilder(outputFile, { name: 'deobfuscated.lua' })]
                });
                fs.unlinkSync(outputFile);
                await statusMsg.delete();
            }
        } catch (error) {
            await statusMsg.edit(`❌ Error: ${error.message.slice(0, 200)}`);
        }
    }
});

client.login(BOT_TOKEN);

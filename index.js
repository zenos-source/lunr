const { Client, GatewayIntentBits, Partials, ActionRowBuilder, ButtonBuilder, ButtonStyle, EmbedBuilder, ModalBuilder, TextInputBuilder, TextInputStyle } = require('discord.js');
const mongoose = require('mongoose');
require('dotenv').config();

const client = new Client({
    intents: [GatewayIntentBits.Guilds, GatewayIntentBits.GuildMessages, GatewayIntentBits.MessageContent, GatewayIntentBits.GuildMembers],
    partials: [Partials.Channel]
});

// Connect to MongoDB
mongoose.connect(process.env.MONGODB_URI);

// Import models
const Project = require('./models/Project');
const License = require('./models/License');

// Store active panels for each server
const activePanels = new Map();

client.once('ready', async () => {
    console.log(`✅ Logged in as ${client.user.tag}`);
    
    // Register slash commands globally
    const commands = [
        { name: 'setpanel', description: 'Create the control panel in this channel' },
        { name: 'whitelist', description: 'Whitelist a user', options: [{ name: 'user', type: 6, required: true }, { name: 'days', type: 4, required: false }] },
        { name: 'unwhitelist', description: 'Remove user from whitelist', options: [{ name: 'user', type: 6, required: true }] },
        { name: 'blacklist', description: 'Blacklist a user', options: [{ name: 'user', type: 6, required: true }, { name: 'reason', type: 3, required: false }] },
        { name: 'force-resethwid', description: 'Force reset user HWID', options: [{ name: 'user', type: 6, required: true }] },
        { name: 'compensate', description: 'Add days to all active keys', options: [{ name: 'days', type: 4, required: true }] },
        { name: 'setlogs', description: 'Set logging webhook', options: [{ name: 'url', type: 3, required: true }] },
    ];
    
    await client.application.commands.set(commands);
    console.log(`✅ Registered ${commands.length} slash commands`);
});

// ============================================
// SLASH COMMANDS
// ============================================

client.on('interactionCreate', async (interaction) => {
    if (!interaction.isCommand()) return;
    
    const { commandName, member, guild, channel } = interaction;
    
    // Check if user has admin perms for manager commands
    const isAdmin = member.permissions.has('Administrator');
    
    // ========== SETPANEL ==========
    if (commandName === 'setpanel') {
        if (!isAdmin) return interaction.reply({ content: '❌ Admin only!', ephemeral: true });
        
        // Get or create project for this guild
        let project = await Project.findOne({ ownerId: guild.ownerId });
        if (!project) {
            project = new Project({
                name: guild.name,
                ownerId: guild.ownerId,
                createdAt: new Date()
            });
            await project.save();
        }
        
        const embed = new EmbedBuilder()
            .setTitle('⚡ GammaHub Control Panel')
            .setDescription(`This control panel is for the project: **${project.name}**\nIf you're a buyer, click the buttons below to redeem your key, get the script or get your role`)
            .setColor(0x5865F2)
            .setFooter({ text: 'Made with ❤️ - Support: discord.gg/support' });
        
        const row = new ActionRowBuilder()
            .addComponents(
                new ButtonBuilder().setCustomId('redeem').setLabel('🎫 Redeem Key').setStyle(ButtonStyle.Primary),
                new ButtonBuilder().setCustomId('script').setLabel('📜 Get Script').setStyle(ButtonStyle.Success),
                new ButtonBuilder().setCustomId('role').setLabel('👑 Get Role').setStyle(ButtonStyle.Secondary),
                new ButtonBuilder().setCustomId('resethwid').setLabel('🔄 Reset HWID').setStyle(ButtonStyle.Danger),
                new ButtonBuilder().setCustomId('status').setLabel('📊 Status').setStyle(ButtonStyle.Secondary)
            );
        
        const message = await channel.send({ embeds: [embed], components: [row] });
        activePanels.set(guild.id, message.id);
        
        await interaction.reply({ content: '✅ Panel created!', ephemeral: true });
    }
    
    // ========== WHITELIST ==========
    if (commandName === 'whitelist') {
        if (!isAdmin) return interaction.reply({ content: '❌ Admin only!', ephemeral: true });
        
        const user = interaction.options.getUser('user');
        const days = interaction.options.getInteger('days') || 30;
        const expiresAt = new Date();
        expiresAt.setDate(expiresAt.getDate() + days);
        
        // Check if already has license
        let license = await License.findOne({ discordId: user.id, isBlacklisted: false });
        
        if (license) {
            license.expiresAt = expiresAt;
            await license.save();
            await interaction.reply({ content: `✅ Updated ${user.tag}'s license! Expires in ${days} days.`, ephemeral: true });
        } else {
            // Generate key
            const key = generateKey();
            license = new License({
                key,
                discordId: user.id,
                discordName: user.tag,
                expiresAt,
                createdAt: new Date()
            });
            await license.save();
            await interaction.reply({ content: `✅ Whitelisted ${user.tag}!\nKey: \`${key}\`\nExpires: ${expiresAt.toDateString()}`, ephemeral: true });
            
            // Try to DM user
            try {
                await user.send(`🎉 You've been whitelisted for **${project?.name || 'GammaHub'}**!\nKey: \`${key}\``);
            } catch(e) {}
        }
    }
    
    // ========== UNWHITELIST ==========
    if (commandName === 'unwhitelist') {
        if (!isAdmin) return interaction.reply({ content: '❌ Admin only!', ephemeral: true });
        const user = interaction.options.getUser('user');
        await License.deleteOne({ discordId: user.id });
        await interaction.reply({ content: `✅ Removed ${user.tag} from whitelist.`, ephemeral: true });
    }
    
    // ========== BLACKLIST ==========
    if (commandName === 'blacklist') {
        if (!isAdmin) return interaction.reply({ content: '❌ Admin only!', ephemeral: true });
        const user = interaction.options.getUser('user');
        const reason = interaction.options.getString('reason') || 'No reason';
        
        await License.findOneAndUpdate(
            { discordId: user.id },
            { isBlacklisted: true, blacklistReason: reason },
            { upsert: true }
        );
        await interaction.reply({ content: `✅ Blacklisted ${user.tag}\nReason: ${reason}`, ephemeral: true });
    }
    
    // ========== FORCE-RESETHWID ==========
    if (commandName === 'force-resethwid') {
        if (!isAdmin) return interaction.reply({ content: '❌ Admin only!', ephemeral: true });
        const user = interaction.options.getUser('user');
        await License.findOneAndUpdate({ discordId: user.id }, { hwid: null });
        await interaction.reply({ content: `✅ Reset HWID for ${user.tag}`, ephemeral: true });
    }
    
    // ========== COMPENSATE ==========
    if (commandName === 'compensate') {
        if (!isAdmin) return interaction.reply({ content: '❌ Admin only!', ephemeral: true });
        const days = interaction.options.getInteger('days');
        await License.updateMany(
            { isBlacklisted: false, isLifetime: false },
            { $inc: { expiresAt: days * 86400000 } }
        );
        await interaction.reply({ content: `✅ Added ${days} days to all active keys!`, ephemeral: true });
    }
    
    // ========== SETLOGS ==========
    if (commandName === 'setlogs') {
        if (!isAdmin) return interaction.reply({ content: '❌ Admin only!', ephemeral: true });
        const url = interaction.options.getString('url');
        let project = await Project.findOne({ ownerId: guild.ownerId });
        if (!project) {
            project = new Project({ name: guild.name, ownerId: guild.ownerId });
        }
        project.webhookUrl = url;
        await project.save();
        await interaction.reply({ content: `✅ Logging webhook set!`, ephemeral: true });
    }
});

// ============================================
// BUTTON HANDLERS
// ============================================

client.on('interactionCreate', async (interaction) => {
    if (!interaction.isButton()) return;
    
    const { customId, user, guild, member } = interaction;
    let license = await License.findOne({ discordId: user.id });
    
    // ========== REDEEM KEY ==========
    if (customId === 'redeem') {
        const modal = new ModalBuilder()
            .setCustomId('redeemModal')
            .setTitle('🎫 Redeem License Key');
        
        const keyInput = new TextInputBuilder()
            .setCustomId('key')
            .setLabel('Enter your license key')
            .setStyle(TextInputStyle.Short)
            .setPlaceholder('XXXX-XXXX-XXXX-XXXX')
            .setRequired(true);
        
        modal.addComponents(new ActionRowBuilder().addComponents(keyInput));
        await interaction.showModal(modal);
    }
    
    // ========== GET SCRIPT ==========
    if (customId === 'script') {
        if (!license || license.isBlacklisted || (license.expiresAt && license.expiresAt < new Date() && !license.isLifetime)) {
            return interaction.reply({ content: '❌ No active license found! Redeem a key first.', ephemeral: true });
        }
        
        const project = await Project.findOne({ ownerId: guild.ownerId });
        const script = `-- GammaHub Loader
-- Licensed to: ${user.tag}
-- Expires: ${license.isLifetime ? 'Lifetime' : license.expiresAt?.toDateString()}

local key = "${license.key}"
local hwid = game:GetService("Players").LocalPlayer.UserId

local function verify()
    local response = game:GetService("HttpService"):JSONDecode(
        game:HttpGet("https://api.yoursite.com/verify?key=" .. key .. "&hwid=" .. hwid)
    )
    return response.valid, response.message
end

local valid, msg = verify()
if valid then
    print("✅ " .. msg)
    loadstring(game:HttpGet("${project.settings.scriptUrl || 'https://your-script-url.lua'}"))()
else
    game:GetService("StarterGui"):SetCore("SendNotification", {
        Title = "License Error",
        Text = msg or "Invalid license",
        Duration = 5
    })
end`;
        
        try {
            await user.send({ content: '📜 **Your Loader Script**', files: [{ attachment: Buffer.from(script), name: 'loader.lua' }] });
            await interaction.reply({ content: '✅ Script sent to your DMs!', ephemeral: true });
        } catch(e) {
            await interaction.reply({ content: '❌ Enable DMs from server members!', ephemeral: true });
        }
    }
    
    // ========== GET ROLE ==========
    if (customId === 'role') {
        if (!license || license.isBlacklisted) {
            return interaction.reply({ content: '❌ No active license found!', ephemeral: true });
        }
        
        const project = await Project.findOne({ ownerId: guild.ownerId });
        if (project.settings.buyerRoleId && project.settings.enableRoleOnRedeem) {
            const role = guild.roles.cache.get(project.settings.buyerRoleId);
            if (role && !member.roles.cache.has(role.id)) {
                await member.roles.add(role);
                await interaction.reply({ content: `✅ Added role: ${role.name}`, ephemeral: true });
            } else {
                await interaction.reply({ content: `ℹ️ You already have the role!`, ephemeral: true });
            }
        } else {
            await interaction.reply({ content: 'ℹ️ Role assignment not configured by server admin.', ephemeral: true });
        }
    }
    
    // ========== RESET HWID ==========
    if (customId === 'resethwid') {
        if (!license) return interaction.reply({ content: '❌ No license found!', ephemeral: true });
        
        const project = await Project.findOne({ ownerId: guild.ownerId });
        const cooldownDays = project.settings.hwidResetCooldown || 7;
        const lastReset = license.lastHwidReset;
        
        if (lastReset) {
            const daysSince = (Date.now() - lastReset) / (1000 * 60 * 60 * 24);
            if (daysSince < cooldownDays) {
                const remaining = Math.ceil(cooldownDays - daysSince);
                return interaction.reply({ content: `⏰ HWID reset on cooldown! Try again in ${remaining} days.`, ephemeral: true });
            }
        }
        
        license.hwid = null;
        license.lastHwidReset = new Date();
        license.hwidResetCount += 1;
        await license.save();
        
        await interaction.reply({ content: '🔄 Your HWID has been reset! You can now activate on a new device.', ephemeral: true });
    }
    
    // ========== STATUS ==========
    if (customId === 'status') {
        if (!license) {
            return interaction.reply({ content: '❌ No license found. Use "Redeem Key" to activate.', ephemeral: true });
        }
        
        if (license.isBlacklisted) {
            return interaction.reply({ content: `❌ Your license is **BLACKLISTED**\nReason: ${license.blacklistReason || 'Violation of terms'}`, ephemeral: true });
        }
        
        const isExpired = license.expiresAt && license.expiresAt < new Date() && !license.isLifetime;
        const status = isExpired ? '❌ EXPIRED' : (license.isLifetime ? '👑 LIFETIME' : '✅ ACTIVE');
        const expires = license.isLifetime ? 'Never' : license.expiresAt?.toDateString() || 'Unknown';
        
        const embed = new EmbedBuilder()
            .setTitle('📊 License Status')
            .setColor(isExpired ? 0xED4245 : 0x57F287)
            .addFields(
                { name: 'Status', value: status, inline: true },
                { name: 'Expires', value: expires, inline: true },
                { name: 'HWID', value: license.hwid ? '🔒 Locked' : '⚠️ Not set', inline: true },
                { name: 'HWID Resets', value: `${license.hwidResetCount || 0} used`, inline: true }
            )
            .setFooter({ text: `License ID: ${license.key}` });
        
        await interaction.reply({ embeds: [embed], ephemeral: true });
    }
});

// ============================================
// MODAL HANDLER (Redeem Key)
// ============================================

client.on('interactionCreate', async (interaction) => {
    if (!interaction.isModalSubmit()) return;
    if (interaction.customId !== 'redeemModal') return;
    
    const key = interaction.fields.getTextInputValue('key').toUpperCase();
    const user = interaction.user;
    
    // Find license by key
    let license = await License.findOne({ key, isBlacklisted: false });
    
    if (!license) {
        return interaction.reply({ content: '❌ Invalid or already used key!', ephemeral: true });
    }
    
    if (license.discordId && license.discordId !== user.id) {
        return interaction.reply({ content: '❌ This key is already linked to another Discord account!', ephemeral: true });
    }
    
    if (license.expiresAt && license.expiresAt < new Date() && !license.isLifetime) {
        return interaction.reply({ content: '❌ This key has expired!', ephemeral: true });
    }
    
    // Link key to user
    license.discordId = user.id;
    license.discordName = user.tag;
    await license.save();
    
    await interaction.reply({ content: `✅ **Key Redeemed!**\nYour license is now linked to ${user.tag}\nExpires: ${license.isLifetime ? 'Lifetime' : license.expiresAt?.toDateString()}`, ephemeral: true });
    
    // Log via webhook
    const project = await Project.findOne({ ownerId: interaction.guild.ownerId });
    if (project?.webhookUrl) {
        // Send webhook notification
    }
});

// Helper function
function generateKey() {
    const chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789';
    let key = '';
    for (let i = 0; i < 4; i++) {
        for (let j = 0; j < 4; j++) {
            key += chars[Math.floor(Math.random() * chars.length)];
        }
        if (i < 3) key += '-';
    }
    return key;
}

client.login(process.env.DISCORD_TOKEN);

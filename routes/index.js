const express = require('express');
const cors = require('cors');
const fs = require('fs');
const path = require('path');

const app = express();
app.use(cors());
app.use(express.json());

// File paths for storing data
const DATA_DIR = path.join(__dirname, 'data');
const LICENSES_FILE = path.join(DATA_DIR, 'licenses.json');
const PROJECTS_FILE = path.join(DATA_DIR, 'projects.json');

// Ensure data directory exists
if (!fs.existsSync(DATA_DIR)) {
    fs.mkdirSync(DATA_DIR);
}

// Initialize files if they don't exist
if (!fs.existsSync(LICENSES_FILE)) {
    fs.writeFileSync(LICENSES_FILE, JSON.stringify([], null, 2));
}
if (!fs.existsSync(PROJECTS_FILE)) {
    fs.writeFileSync(PROJECTS_FILE, JSON.stringify([], null, 2));
}

// Helper functions
function getLicenses() {
    const data = fs.readFileSync(LICENSES_FILE);
    return JSON.parse(data);
}

function saveLicenses(licenses) {
    fs.writeFileSync(LICENSES_FILE, JSON.stringify(licenses, null, 2));
}

function getProjects() {
    const data = fs.readFileSync(PROJECTS_FILE);
    return JSON.parse(data);
}

function saveProjects(projects) {
    fs.writeFileSync(PROJECTS_FILE, JSON.stringify(projects, null, 2));
}

// Generate random key
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

// ============================================
// API ROUTES
// ============================================

// Verify license (called by Lua script)
app.get('/verify', (req, res) => {
    const { key, hwid } = req.query;
    const licenses = getLicenses();
    
    const license = licenses.find(l => l.key === key);
    
    if (!license) {
        return res.json({ valid: false, message: 'Invalid license key' });
    }
    
    if (license.isBlacklisted) {
        return res.json({ valid: false, message: 'License blacklisted' });
    }
    
    if (!license.isLifetime && license.expiresAt && new Date(license.expiresAt) < new Date()) {
        return res.json({ valid: false, message: 'License expired' });
    }
    
    // HWID check
    if (license.hwid && license.hwid !== hwid) {
        return res.json({ valid: false, message: 'HWID mismatch - Use Reset HWID button' });
    }
    
    // First time - set HWID
    if (!license.hwid && hwid) {
        license.hwid = hwid;
        saveLicenses(licenses);
    }
    
    license.lastExecution = new Date();
    license.executionCount = (license.executionCount || 0) + 1;
    saveLicenses(licenses);
    
    res.json({
        valid: true,
        message: 'License valid',
        expires: license.expiresAt,
        isLifetime: license.isLifetime
    });
});

// Generate new license key (admin use)
app.post('/generate', (req, res) => {
    const { days, note } = req.body;
    const expiresAt = new Date();
    expiresAt.setDate(expiresAt.getDate() + (days || 30));
    
    const newLicense = {
        key: generateKey(),
        discordId: null,
        discordName: null,
        hwid: null,
        hwidResetCount: 0,
        lastHwidReset: null,
        expiresAt: days === 0 ? null : expiresAt,
        isLifetime: days === 0,
        isBlacklisted: false,
        blacklistReason: null,
        note: note || null,
        executionCount: 0,
        createdAt: new Date()
    };
    
    const licenses = getLicenses();
    licenses.push(newLicense);
    saveLicenses(licenses);
    
    res.json({ success: true, key: newLicense.key });
});

// Get license info
app.get('/license/:key', (req, res) => {
    const licenses = getLicenses();
    const license = licenses.find(l => l.key === req.params.key);
    
    if (!license) {
        return res.status(404).json({ error: 'License not found' });
    }
    
    res.json(license);
});

// List all licenses
app.get('/licenses', (req, res) => {
    const licenses = getLicenses();
    res.json(licenses);
});

// Delete license
app.delete('/license/:key', (req, res) => {
    let licenses = getLicenses();
    licenses = licenses.filter(l => l.key !== req.params.key);
    saveLicenses(licenses);
    res.json({ success: true });
});

// Blacklist license
app.post('/blacklist', (req, res) => {
    const { key, reason } = req.body;
    const licenses = getLicenses();
    const license = licenses.find(l => l.key === key);
    
    if (license) {
        license.isBlacklisted = true;
        license.blacklistReason = reason || 'No reason';
        saveLicenses(licenses);
        res.json({ success: true });
    } else {
        res.status(404).json({ error: 'License not found' });
    }
});

// Reset HWID
app.post('/resethwid', (req, res) => {
    const { key } = req.body;
    const licenses = getLicenses();
    const license = licenses.find(l => l.key === key);
    
    if (license) {
        license.hwid = null;
        license.lastHwidReset = new Date();
        license.hwidResetCount = (license.hwidResetCount || 0) + 1;
        saveLicenses(licenses);
        res.json({ success: true });
    } else {
        res.status(404).json({ error: 'License not found' });
    }
});

// Add days to license
app.post('/adddays', (req, res) => {
    const { key, days } = req.body;
    const licenses = getLicenses();
    const license = licenses.find(l => l.key === key);
    
    if (license && !license.isLifetime) {
        const currentExpiry = license.expiresAt ? new Date(license.expiresAt) : new Date();
        currentExpiry.setDate(currentExpiry.getDate() + days);
        license.expiresAt = currentExpiry;
        saveLicenses(licenses);
        res.json({ success: true, newExpiry: license.expiresAt });
    } else {
        res.status(404).json({ error: 'License not found or is lifetime' });
    }
});

// ============================================
// START SERVER
// ============================================

const PORT = process.env.PORT || 3000;
app.listen(PORT, () => {
    console.log(`
    ╔══════════════════════════════════╗
    ║     Licensing API Server         ║
    ║     Running on port ${PORT}        ║
    ╚══════════════════════════════════╝
    `);
    console.log(`✅ API: http://localhost:${PORT}`);
    console.log(`📋 Verify endpoint: http://localhost:${PORT}/verify?key=XXXX&hwid=XXXX`);
});

const express = require('express');
const router = express.Router();
const License = require('../models/License');

router.get('/verify', async (req, res) => {
    const { key, hwid } = req.query;
    
    const license = await License.findOne({ key });
    
    if (!license) {
        return res.json({ valid: false, message: 'Invalid license key' });
    }
    
    if (license.isBlacklisted) {
        return res.json({ valid: false, message: 'License blacklisted' });
    }
    
    if (!license.isLifetime && license.expiresAt < new Date()) {
        return res.json({ valid: false, message: 'License expired' });
    }
    
    // Check HWID
    if (license.hwid && license.hwid !== hwid) {
        return res.json({ valid: false, message: 'HWID mismatch - Use Reset HWID button' });
    }
    
    // First time - set HWID
    if (!license.hwid && hwid) {
        license.hwid = hwid;
    }
    
    license.lastExecution = new Date();
    license.executionCount += 1;
    await license.save();
    
    res.json({
        valid: true,
        message: 'License valid',
        expires: license.isLifetime ? null : license.expiresAt,
        variables: license.variables || {}
    });
});

module.exports = router;

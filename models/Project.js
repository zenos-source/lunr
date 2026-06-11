const projectSchema = {
    name: String,
    ownerId: String, // Discord ID
    ownerEmail: String,
    webhookUrl: String, // Logging webhook
    settings: {
        hwidLock: { type: Boolean, default: true },
        hwidResetCooldown: { type: Number, default: 7 }, // days
        buyerRoleId: String,
        enableRoleOnRedeem: { type: Boolean, default: false },
        scriptUrl: String,
        scriptVersion: { type: String, default: "1.0.0" }
    },
    createdAt: Date
};

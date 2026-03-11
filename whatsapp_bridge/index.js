const { Client, LocalAuth } = require('whatsapp-web.js');
const qrcode = require('qrcode-terminal');
const express = require('express');
const axios = require('axios');

const app = express();
app.use(express.json());

const QRCode = require('qrcode');
let currentQR = null;

// Expose a route so the user can see the QR on a white background browser page
app.get('/qr', async (req, res) => {
    if (!currentQR) {
        return res.send('<h2>No QR code to scan right now (either loading or already connected).</h2><script>setTimeout(() => location.reload(), 2000)</script>');
    }
    try {
        const qrImage = await QRCode.toDataURL(currentQR);
        res.send(`
            <div style="font-family: sans-serif; text-align: center; margin-top: 50px;">
                <h2>Scan with WhatsApp Linking</h2>
                <img src="${qrImage}" style="width: 300px; height: 300px; border: 1px solid #ccc; padding: 10px; border-radius: 8px;" />
                <p>Ensure your phone's screen is on and the camera lens is clean.</p>
                <script>
                    // refresh occasionally to catch an updated QR code
                    setTimeout(() => location.reload(), 5000);
                </script>
            </div>
        `);
    } catch (e) {
        res.send('Error generating QR Image');
    }
});

const fs = require('fs');

// Try to find a local browser executable since we skipped the download
const browserPaths = [
    'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe',
    'C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe',
    'C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe'
];
const executablePath = browserPaths.find(p => fs.existsSync(p)) || null;

// Set up the WhatsApp client with LocalAuth so we don't need to scan the QR code every time
const client = new Client({
    authStrategy: new LocalAuth({ dataPath: './wwebjs_auth' }),
    puppeteer: {
        executablePath: executablePath,
        headless: 'new', // Use newer headless mode if available
        args: [
            '--no-sandbox',
            '--disable-setuid-sandbox',
            '--disable-dev-shm-usage',
            '--disable-extensions',
            '--no-zygote'
        ]
    }
});

client.on('qr', (qr) => {
    // Save it for the web endpoint
    currentQR = qr;

    // Generate and scan this code with your phone
    console.log('\n--- SCAN THIS QR CODE AT http://localhost:3000/qr ---');
    qrcode.generate(qr, { small: true });
});

client.on('ready', () => {
    console.log('WhatsApp connection is READY!');
    currentQR = null; // clear it out
});

client.on('message', async msg => {
    // Ignore status broadcasts and empty messages
    if (msg.isStatus || !msg.body) return;

    try {
        console.log(`[Incoming] ${msg.from}: ${msg.body}`);

        // Forward the message to our Python agent backend
        // Assume Flask runs on port 5000
        await axios.post('http://127.0.0.1:5000/api/whatsapp/incoming', {
            id: msg.id._serialized,
            from: msg.from,
            author: msg.author || msg.from,
            body: msg.body,
            timestamp: msg.timestamp,
            hasMedia: msg.hasMedia
        });

    } catch (err) {
        console.error('Error forwarding message to Python backend:', err.message);
    }
});

client.initialize();

// REST endpoint for the Python backend to send messages back to WhatsApp
app.post('/send', async (req, res) => {
    const { to, message } = req.body;
    if (!to || !message) {
        return res.status(400).json({ error: 'Missing "to" or "message" fields' });
    }

    try {
        // Enforce the WhatsApp internal ID suffix if it's missing (needed for proactive messages)
        let chatId = to;
        if (!chatId.includes('@c.us') && !chatId.includes('@g.us')) {
            chatId = `${chatId.replace(/[^0-9]/g, '')}@c.us`;
        }

        // Send a message exactly how we do for replies
        const sentMsg = await client.sendMessage(chatId, message);
        res.json({ success: true, messageId: sentMsg.id._serialized });
        console.log(`[Outgoing] ${to}: ${message}`);
    } catch (err) {
        console.error('Error sending WhatsApp message:', err.message);
        const errStr = err.message || "";
        if (errStr.includes("t: t") || errStr.includes("evaluate") || errStr.includes("undefined")) {
            return res.status(400).json({ error: "WhatsApp Web rejected the phone number format. Ensure the number includes the exact International Country Code WITHOUT a leading zero or '+' symbol (e.g. use '923350806140' instead of '03350806140')." });
        }
        res.status(500).json({ error: err.message });
    }
});

app.post('/logout', async (req, res) => {
    try {
        await client.logout();
        console.log('Successfully logged out of WhatsApp.');
        res.json({ success: true, message: 'Logged out successfully' });
    } catch (err) {
        console.error('Error logging out:', err);
        res.status(500).json({ error: err.message });
    }
});

app.get('/status', (req, res) => {
    res.json({
        status: client.info ? 'online' : 'offline',
        qr_active: !!currentQR,
        info: client.info || null
    });
});

const PORT = 3000;
app.listen(PORT, () => {
    console.log(`WhatsApp Bridge Server running on http://localhost:${PORT}`);
});

const { Client, LocalAuth, MessageMedia } = require('whatsapp-web.js');
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
    webVersionTimerMS: 60000,
    authTimeoutMs: 60000,
    webVersion: '2.24.12.54',
    webVersionCache: {
        type: 'remote',
        remotePath: 'https://raw.githubusercontent.com/wppconnect-team/wa-version/main/html/2.24.12.54.html',
    },
    puppeteer: {
        executablePath: executablePath,
        headless: true,
        args: [
            '--no-sandbox',
            '--disable-setuid-sandbox',
            '--disable-dev-shm-usage',
            '--disable-extensions',
            '--no-zygote',
            '--dns-servers=8.8.8.8,1.1.1.1',
            '--proxy-server="direct://"',
            '--proxy-bypass-list=*',
            '--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36'
        ]
    }
});

client.on('qr', (qr) => {
    currentQR = qr;
    console.log('\n--- SCAN THIS QR CODE AT http://localhost:3000/qr ---');
    qrcode.generate(qr, { small: true });
});

client.on('loading_screen', (percent, message) => {
    console.log('LOADING SCREEN:', percent, message);
});

client.on('authenticated', () => {
    console.log('AUTHENTICATED');
});

client.on('auth_failure', msg => {
    console.error('AUTHENTICATION FAILURE', msg);
});

client.on('ready', () => {
    console.log('WhatsApp connection is READY!');
    currentQR = null;
});

client.on('disconnected', (reason) => {
    console.log('Client was logged out', reason);
});

client.on('message', async msg => {
    // Ignore status broadcasts and empty messages
    if (msg.isStatus || !msg.body) return;

    try {
        console.log(`[Incoming] ${msg.from}: ${msg.body}`);

        // Media Handling
        let mediaPath = null;
        if (msg.hasMedia) {
            try {
                const media = await msg.downloadMedia();
                if (media) {
                    const mediaDir = './media_inbox';
                    if (!fs.existsSync(mediaDir)) fs.mkdirSync(mediaDir);

                    const filename = msg.id.id + (media.filename ? '_' + media.filename : '');
                    // For safety, remove some special characters from filename
                    const safeFilename = filename.replace(/[^a-z0-9.]/gi, '_').substring(0, 50);
                    const ext = media.mimetype.split('/')[1] || 'bin';
                    let finalFilename = safeFilename;
                    if (!finalFilename.includes('.')) finalFilename += '.' + ext;

                    mediaPath = require('path').resolve(mediaDir, finalFilename);
                    fs.writeFileSync(mediaPath, Buffer.from(media.data, 'base64'));
                    console.log(`[Media] Saved to: ${mediaPath}`);
                }
            } catch (mediaErr) {
                console.error('Error downloading media:', mediaErr.message);
            }
        }

        // Forward the message to our Python agent backend
        await axios.post('http://127.0.0.1:5000/api/whatsapp/incoming', {
            id: msg.id._serialized,
            from: msg.from,
            author: msg.author || msg.from,
            body: msg.body,
            timestamp: msg.timestamp,
            hasMedia: msg.hasMedia,
            mediaPath: mediaPath
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

// REST endpoint for the Python backend to send Images/Media back to WhatsApp
app.post('/send_media', async (req, res) => {
    const { to, filePath, caption } = req.body;
    if (!to || !filePath) {
        return res.status(400).json({ error: 'Missing "to" or "filePath" fields' });
    }

    try {
        if (!fs.existsSync(filePath)) {
            return res.status(404).json({ error: 'File not found on disk: ' + filePath });
        }

        // Enforce the WhatsApp internal ID suffix
        let chatId = to;
        if (!chatId.includes('@c.us') && !chatId.includes('@g.us')) {
            chatId = `${chatId.replace(/[^0-9]/g, '')}@c.us`;
        }

        const media = MessageMedia.fromFilePath(filePath);
        const options = caption ? { caption: caption } : {};

        const sentMsg = await client.sendMessage(chatId, media, options);
        res.json({ success: true, messageId: sentMsg.id._serialized });
        console.log(`[Outgoing Media] ${to}: ${filePath}`);
    } catch (err) {
        console.error('Error sending WhatsApp media:', err.message);
        res.status(500).json({ error: err.message });
    }
});

// REST endpoint to block a contact
app.post('/block', async (req, res) => {
    const { contactId } = req.body;
    if (!contactId) return res.status(400).json({ error: 'Missing "contactId"' });

    try {
        let chatId = contactId;
        if (!chatId.includes('@c.us') && !chatId.includes('@g.us')) {
            chatId = `${chatId.replace(/[^0-9]/g, '')}@c.us`;
        }
        const contact = await client.getContactById(chatId);
        await contact.block();
        res.json({ success: true, message: `Contact ${chatId} blocked.` });
        console.log(`[Blocked] ${chatId}`);
    } catch (err) {
        console.error('Error blocking contact:', err.message);
        res.status(500).json({ error: err.message });
    }
});

// REST endpoint to unblock a contact
app.post('/unblock', async (req, res) => {
    const { contactId } = req.body;
    if (!contactId) return res.status(400).json({ error: 'Missing "contactId"' });

    try {
        let chatId = contactId;
        if (!chatId.includes('@c.us') && !chatId.includes('@g.us')) {
            chatId = `${chatId.replace(/[^0-9]/g, '')}@c.us`;
        }
        const contact = await client.getContactById(chatId);
        await contact.unblock();
        res.json({ success: true, message: `Contact ${chatId} unblocked.` });
        console.log(`[Unblocked] ${chatId}`);
    } catch (err) {
        console.error('Error unblocking contact:', err.message);
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

const { default: makeWASocket, useMultiFileAuthState, DisconnectReason } = require('@whiskeysockets/baileys');
const qrcode = require('qrcode-terminal');
const axios = require('axios');
const fs = require('fs');
require('dotenv').config();

const SYNAPSE_API = process.env.SYNAPSE_API || "http://127.0.0.1:8000/api/command";
// We might need a port to receive commands from Python, or just poll. 
// For V1, we will just act as a client (Input -> API). 
// Responses will be handled by Synapse calling a webhook? Or us polling?
// Wait, run_bot.py polls. We should probably poll too or set up a simple Express server if we want push.
// Let's stick to the run_bot.py pattern: Poll for the task result after sending.

async function connectToWhatsApp() {
    const { state, saveCreds } = await useMultiFileAuthState('auth_info_baileys');

    const sock = makeWASocket({
        printQRInTerminal: false,
        auth: state,
        browser: ["Mac OS", "Chrome", "10.15.7"],
    });

    sock.ev.on('creds.update', saveCreds);

    sock.ev.on('connection.update', (update) => {
        const { connection, lastDisconnect, qr } = update;

        if (qr) {
            console.log('\n[WhatsApp] Please scan the QR code below:\n');
            qrcode.generate(qr, { small: true });
        }

        if (connection === 'close') {
            const shouldReconnect = (lastDisconnect.error)?.output?.statusCode !== DisconnectReason.loggedOut;
            console.log('connection closed due to ', lastDisconnect.error, ', reconnecting ', shouldReconnect);
            if (shouldReconnect) {
                connectToWhatsApp();
            }
        } else if (connection === 'open') {
            console.log('opened connection');
        }
    });

    sock.ev.on('messages.upsert', async (m) => {
        const msg = m.messages[0];

        // Extract text early to check for commands
        const text = msg.message?.conversation || msg.message?.extendedTextMessage?.text || msg.message?.imageMessage?.caption;
        if (!text) return;

        // Allow 'fromMe' ONLY if it looks like a command (to support Note to Self testing)
        // We avoid infinite loops by assuming bot replies don't start with '/'
        const isCommand = text.trim().startsWith('/');

        if ((!msg.key.fromMe || isCommand) && m.type === 'notify') {
            const remoteJid = msg.key.remoteJid;

            console.log(`Received message from ${remoteJid}: ${text}`);

            try {
                // Forward to Synapse
                const response = await axios.post(SYNAPSE_API, { text: text });

                if (response.status === 200) {
                    const taskId = response.data.task_id;
                    await sock.sendMessage(remoteJid, { text: `Command Queued (Task ${taskId})...` });

                    // Poll for result (simulating run_bot.py logic)
                    pollTaskResult(sock, remoteJid, taskId);
                }
            } catch (error) {
                console.error('Error sending to Synapse API:', error.message);
                await sock.sendMessage(remoteJid, { text: `Error connecting to Synapse: ${error.message}` });
            }
        }
    });
}

async function pollTaskResult(sock, jid, taskId) {
    let attempts = 0;
    const maxAttempts = 60; // 120 seconds

    const interval = setInterval(async () => {
        attempts++;
        if (attempts > maxAttempts) {
            clearInterval(interval);
            await sock.sendMessage(jid, { text: "Task timed out." });
            return;
        }

        try {
            // Need the full URL for task status. Assuming standard Synapse endpoints.
            // The taskId is unique.
            const statusUrl = `http://127.0.0.1:8000/api/task/${taskId}`;
            const res = await axios.get(statusUrl);

            if (res.status === 200) {
                const data = res.data;
                if (data.status === "DONE") {
                    clearInterval(interval);

                    // Send result
                    let message = "";
                    let files = [];

                    try {
                        // Synapse might return JSON string in 'result'
                        if (typeof data.result === 'string') {
                            try {
                                const parsed = JSON.parse(data.result);
                                message = parsed.message || data.result;
                                files = parsed.files || [];
                            } catch {
                                message = data.result;
                            }
                        } else {
                            message = data.result?.message || JSON.stringify(data.result);
                            files = data.result?.files || [];
                        }
                    } catch (e) {
                        message = String(data.result);
                    }

                    if (message) {
                        await sock.sendMessage(jid, { text: message });
                    }

                    // Handle files (Experimental)
                    if (files && files.length > 0) {
                        for (const file of files) {
                            if (fs.existsSync(file)) {
                                await sock.sendMessage(jid, { text: `Uploading ${file}...` });
                                // Baileys doesn't support streaming local files directly in all versions easily without mimetype
                                // We will just send text notification for now to avoid complexity, or try document.
                                // For now: just text.
                                await sock.sendMessage(jid, { text: `[File Generated: ${file}]` });
                            }
                        }
                    }

                } else if (data.status === "FAILED") {
                    clearInterval(interval);
                    await sock.sendMessage(jid, { text: `Task Failed: ${data.error}` });
                }
            }
        } catch (e) {
            console.log("Polling error:", e.message);
        }

    }, 2000);
}

connectToWhatsApp();

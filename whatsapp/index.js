const { Client, LocalAuth } = require('whatsapp-web.js');
const fetch = require('node-fetch');
const qrcode = require('qrcode-terminal');

// Initialize WhatsApp client with authentication
const client = new Client({
    authStrategy: new LocalAuth(),
    puppeteer: {
        headless: true,
        args: ['--no-sandbox', '--disable-setuid-sandbox']
    }
});

// Payment configuration
const PAYMENT_NUMBERS = [
    '02111009378995',
    'PK62ALFH0211001009378995'
];
const ADMIN_NUMBER = '923705208893@c.us'; // Replace with your number in this format

// QR Code generation for authentication
client.on('qr', (qr) => {
    console.log('Scan this QR code to authenticate your WhatsApp account:');
    qrcode.generate(qr, { small: true });
});

// Connection status updates
client.on('authenticated', () => {
    console.log('✅ Authentication successful!');
});

client.on('auth_failure', (msg) => {
    console.error('❌ Authentication failed:', msg);
});

client.on('loading_screen', (percent, message) => {
    console.log(`🔄 Loading: ${percent}% - ${message}`);
});

client.on('disconnected', (reason) => {
    console.log('❌ Client was logged out:', reason);
});

client.on('ready', () => {
    console.log('✅ WhatsApp bot is ready and connected!');
});

// Improved message handling
client.on('message', async (message) => {
    if (message.from === 'status@broadcast') return;
    const userMessage = message.body;
    const userPhone = message.from;

    if (!userMessage || userMessage.trim() === '') return;

    console.log(`📩 Received message from ${userPhone}: ${userMessage}`);

    try {
        // Get the chat object safely
        const chat = await message.getChat();
        
        // Try to send typing indicator (if available)
        try {
            if (chat.sendStateTyping) {
                await chat.sendStateTyping();
            }
        } catch (typingError) {
            console.log('Typing indicator not available');
        }

        // Process message through FastAPI
        const response = await fetch('http://127.0.0.1:8000/chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                message: userMessage,
                user_id: userPhone
            }),
        });

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const data = await response.json();
        console.log('⚡ Response from FastAPI:', data.reply);

        if (data.reply) {
            // Send reply to user
            await message.reply(data.reply);
            console.log(`📤 Sent reply to ${userPhone}`);

            // Check for payment information
            const containsPayment = PAYMENT_NUMBERS.some(number => 
                data.reply.includes(number)
            );
            
            if (containsPayment) {
                try {
                    const alertMsg = `🚨 Payment Alert!\n\nSent to: ${userPhone}\n\nMessage:\n${data.reply}`;
                    await client.sendMessage(ADMIN_NUMBER, alertMsg);
                    console.log(`⚠️ Payment alert sent to admin`);
                } catch (alertError) {
                    console.error('Failed to send payment alert:', alertError);
                }
            }
        } else {
            await message.reply('⚠️ Sorry, I didn\'t understand that. Please try again.');
        }
    } catch (error) {
        console.error('❌ Error processing message:', error);
        try {
            await client.sendMessage(userPhone, '⚠️ Sorry! Something went wrong. Please try again later.');
        } catch (sendError) {
            console.error('Failed to send error message:', sendError);
        }
    }
});

// Start the bot
client.initialize();
console.log('🚀 WhatsApp bot is initializing...');

// Error handling
process.on('unhandledRejection', (error) => {
    console.error('Unhandled rejection:', error);
});

process.on('uncaughtException', (error) => {
    console.error('Uncaught exception:', error);
});

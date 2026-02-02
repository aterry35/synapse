# Synapse v2.2 - Agentic Plugin Orchestrator 🧠🔌

**Synapse** is a modular, AI-powered bot framework designed to act as an intelligent agent on your system. It combines a Telegram interface, a Web Dashboard, and a hot-swappable plugin architecture to perform complex tasks ranging from coding to browser automation.

![Dashboard Preview](web/dashboard_preview.png)
*(Note: Add a screenshot here)*

## 🚀 Features

### 1. **GCLI (Google CLI Agent)** 👨‍💻
*   **Autonomous Coding**: Generates full projects (React, Python, etc.) from natural language prompts.
*   **SDLC Management**: Handles Creation, Building (npm/pip), and Auto-Fixing of errors.
*   **Result**: Delivers code directly to your `Projects/` folder.

### 2. **System Control** 🖥️
*   **Browser Automation**: Opens a real Chrome browser to perform tasks.
    *   `/sysctl find cost of iphone 15` (Price Checking)
    *   `/sysctl play <video>` (YouTube Playback)
    *   `/sysctl download <url>` (File Acquisition)
*   **Terminal Access**: Execute safe shell commands via chat.

### 3. **Smart Price Engine** 🏷️
*   **Multi-Site Scraping**: Checks Amazon, eBay, and Slickdeals simultaneously.
*   **AI Analysis**: Uses Gemini IQ to identify the *real* product and filter out accessories.
*   **Best Deal**: Returns a single, direct link to the absolute best price.
*   **Command**: `/deals <product name>`

### 4. **Plugin Architecture** 🧩
*   **Modular**: Drop new Python scripts into `app/plugins/` to extend functionality instantly.
*   **Orchestrator**: Manages task queues, locking, and concurrency.
*   **Web Dashboard**: A Cyberpunk-themed UI (v2.2) to monitor logs and control agents.

### 5. **WhatsApp Bridge** 🟢
*   **Integration**: Uses `@whiskeysockets/baileys` to run a headless WhatsApp Web client.
*   **Capabilities**:
    *   Receives commands via "Note to Self" or DMs.
    *   Replies directly in the chat.
    *   Resilient auto-reconnect logic.

---

## 🛠️ Installation

1.  **Clone the Repository**
    ```bash
    git clone https://github.com/aterry35/synapse.git
    cd synapse
    ```

2.  **Setup Environment**
    Copy the example env file and add your keys:
    ```bash
    cp example.env .env
    # Edit .env and add:
    # TELEGRAM_TOKEN=your_bot_token
    # GOOGLE_API_KEY=your_gemini_key
    ```

3.  **Install Dependencies**
    ```bash
    pip3 install -r requirements.txt
    ```

4.  **Run Synapse**
    Use the one-button start script:
    ```bash
    ./start_synapse.sh
    ```
    *   **Dashboard**: `http://127.0.0.1:8000/`
    *   **Telegram**: `https://t.me/your_bot_username`
    *   **WhatsApp**: Scan the QR code in the terminal!

---

## 📱 Communication & Usage

### 1. Telegram
*   **Setup**: Create a bot via `@BotFather` and add the token to `.env`.
*   **Usage**: Simply DM the bot. It supports all commands.
*   **Pros**: Rich UI, buttons, immediate response.

### 2. WhatsApp (Beta)
*   **Setup**: 
    1.  Start Synapse (`./start_synapse.sh`).
    2.  Watch the terminal for a **QR Code**.
    3.  Scan it with your phone (WhatsApp > Linked Devices > Link a Device).
*   **Usage**: 
    *   DM your own number ("Note to Self").
    *   Start message with `/` (e.g., `/deals iphone 16`).
*   **Pros**: Convenience, works on existing account.

---



## 🔮 Future Roadmap

We are building the ultimate AI Assistant. Here's what's coming:
*   [ ] **Voice Interface**: Real-time voice interaction via WebSockets.
*   [ ] **Docker Integration**: Sandboxed execution for generated code.
*   [ ] **Memory Module**: Long-term memory using Vector Databases.
*   [ ] **Marketplace**: A registry for community plugins.

---

## 🤝 Contributing & Community

**We need YOU!** Synapse is an open platform.
If you have an idea for a plugin (e.g., Home Automation, Crypto Trading, Data Analysis), build it and submit a PR!

### How to Build a Plugin
All plugins live in the `app/plugins/` directory. Synapse automatically discovers and loads them on startup.

👉 **[Read the Plugin Development Guide](PLUGIN_GUIDE.md)** for step-by-step instructions.

### Submission Process
1.  Fork the repo.
2.  Create your branch (`git checkout -b plugin/AmazingPlugin`).
3.  Commit your changes (`git commit -m 'Add AmazingPlugin'`).
4.  Push to the branch (`git push origin plugin/AmazingPlugin`).
5.  Open a Pull Request.

**Join the revolution.** Let's build the future of Agentic AI together.

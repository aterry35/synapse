# Synapse Setup & Configuration Guide

## 1. Subscriptions & API Keys

Synapse supports multiple LLM providers. On startup you will be prompted to select one and enter its API key.

### A. Google Gemini API Key (Gemini)
1.  **Cost**: Free tier available (rate limited) or Pay-as-you-go.
2.  **How to Get**:
    - Go to [Google AI Studio](https://aistudio.google.com/).
    - Click **Get API Key**.
    - Create a key in a new or existing Google Cloud project.
    - Copy the key string (starts with `AIza...`).

### B. OpenAI API Key (GPT)
1.  **Cost**: Pay-as-you-go.
2.  **How to Get**:
    - Go to the OpenAI dashboard.
    - Create an API key.

### C. Anthropic API Key (Claude)
1.  **Cost**: Pay-as-you-go.
2.  **How to Get**:
    - Go to the Anthropic console.
    - Create an API key.

### B. Telegram Bot Token (Optional but Recommended)
For mobile control via Telegram.
1.  **Cost**: Free.
2.  **How to Get**:
    - Open Telegram and search for **@BotFather**.
    - Send the command `/newbot`.
    - Follow instructions to name your bot (e.g., `MySynapseBot`).
    - BotFather will give you a **Token** (e.g., `123456:ABC-DEF...`).

---

## 2. Configuration (`.env`)

You must configure the `.env` file in the root directory `/Synapse/.env`.

```bash
# /Synapse/.env

TELEGRAM_TOKEN=123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11
LLM_PROVIDER=gemini
GOOGLE_API_KEY=AIzaSyD-1234567890abcdef1234567890
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=...
```

---

## 3. Installing Google Cloud SDK (for GCLI Plugin)

The "Google CLI Agent" (GCLI Plugin) in Synapse relies on the Google Cloud SDK (`gcloud`) being installed and authenticated on the host machine.

### Installation
1.  **Download**: Visit [Google Cloud CLI Install Page](https://cloud.google.com/sdk/docs/install).
2.  **Install**: Run the installer for Windows.
3.  **Initialize**:
    Open a terminal (PowerShell) and run:
    ```powershell
    gcloud init
    ```
    - Log in with your Google Account.
    - Select your project.

### Configuring Default Credentials
For Python tools (like Gemini clients) to work seamlessly with local auth:
```powershell
gcloud auth application-default login
```
This command ensures that any Google library running on your machine can verify your identity.

---

## 4. Linking Telegram

Once your `.env` has the `TELEGRAM_TOKEN`:
1.  **Start Synapse**: `uvicorn app.main:app --reload`
2.  **Start the Bot**:
    - Run the `python run_bot.py` script (see code below).

### Create `run_bot.py` in root:
```python
import os
import asyncio
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, filters
from dotenv import load_dotenv
import requests

load_dotenv()

SYNAPSE_API = "http://127.0.0.1:8000/api/command"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_message(chat_id=update.effective_chat.id, text="Synapse Connected. Use /ag, /gcli, or /sys commands.")

async def handle_msg(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    # Forward to Synapse API
    try:
        res = requests.post(SYNAPSE_API, json={"text": text})
        if res.status_code == 200:
            await context.bot.send_message(chat_id=update.effective_chat.id, text="Command Queued.")
        else:
            await context.bot.send_message(chat_id=update.effective_chat.id, text=f"API Error: {res.status_code}")
    except Exception as e:
        await context.bot.send_message(chat_id=update.effective_chat.id, text=f"Connection Error: {e}")

if __name__ == '__main__':
    t = os.getenv("TELEGRAM_TOKEN")
    if not t:
        print("Error: TELEGRAM_TOKEN not found in .env")
        exit(1)
        
    app = ApplicationBuilder().token(t).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_msg))
    
    print("Bot Polling...")
    app.run_polling()
```

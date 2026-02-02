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
        # We assume Synapse is running locally
        res = requests.post(SYNAPSE_API, json={"text": text})
        
        if res.status_code == 200:
            data = res.json()
            task_id = data.get("task_id")
            
            await context.bot.send_message(chat_id=update.effective_chat.id, text=f"Command Queued (Task {task_id})...")
            
            # Poll for result
            for _ in range(30): # 60 seconds timeout
                await asyncio.sleep(2)
                try:
                    import json
                    r_status = requests.get(f"http://127.0.0.1:8000/api/task/{task_id}")
                    if r_status.status_code == 200:
                        t_data = r_status.json()
                        status = t_data.get("status")
                        
                        if status == "DONE":
                            raw_result = t_data.get("result", "")
                            # Try Parse JSON
                            try:
                                res_obj = json.loads(raw_result)
                                message = res_obj.get("message", str(raw_result))
                                files = res_obj.get("files", [])
                            except:
                                message = str(raw_result)
                                files = []
                                
                            await context.bot.send_message(chat_id=update.effective_chat.id, text=message)
                            
                            # Send Files
                            for fpath in files:
                                if os.path.exists(fpath):
                                    await context.bot.send_message(chat_id=update.effective_chat.id, text=f"Uploading {os.path.basename(fpath)}...")
                                    with open(fpath, 'rb') as f:
                                        await context.bot.send_document(chat_id=update.effective_chat.id, document=f)
                            return
                        elif status == "FAILED":
                            await context.bot.send_message(chat_id=update.effective_chat.id, text=f"Error: {t_data.get('error')}")
                            return
                except Exception as e:
                    print(f"Polling Error: {e}")
                    pass
            
            await context.bot.send_message(chat_id=update.effective_chat.id, text="Task timed out (check logs).")
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
    # Handle ALL text messages including commands that aren't /start
    app.add_handler(MessageHandler(filters.TEXT, handle_msg))
    
    print("Bot Polling...")
    app.run_polling()

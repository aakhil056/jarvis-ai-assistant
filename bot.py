
##("8505005605:AAHlPDk7fIe_gGFUUiy5Nxwkv_rJF7u-FBE")

import os
import json
import requests
import pytesseract
from PIL import Image
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
)

# -----------------------------
# CONFIG
# -----------------------------
OLLAMA_URL = "http://127.0.0.1:11434/api/generate"  # ✅ FIXED
MODEL = "llama3"

user_memory = {}

# -----------------------------
# COMMANDS
# -----------------------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🤖 Jarvis Activated! Send text, voice, or image.")

async def stop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🛑 Stopped.")

async def clear(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.chat_id
    user_memory[user_id] = []
    await update.message.reply_text("🧹 Memory cleared.")

# -----------------------------
# MAIN REPLY FUNCTION
# -----------------------------
async def reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.chat_id

    if user_id not in user_memory:
        user_memory[user_id] = []

    user_msg = ""

    # =======================
    # 📝 TEXT
    # =======================
    if update.message.text:
        user_msg = update.message.text

    # =======================
    # 🎤 VOICE (optional)
    # =======================
    elif update.message.voice:
        file = await update.message.voice.get_file()
        await file.download_to_drive("voice.ogg")

        os.system("ffmpeg -i voice.ogg voice.wav -y")

        try:
            user_msg = speech_to_text("voice.wav")
        except:
            await update.message.reply_text("❌ Couldn't understand voice")
            return

    # =======================
    # 🖼️ IMAGE
    # =======================
    elif update.message.photo:
        caption = update.message.caption or ""

        if any(word in caption.lower() for word in ["read", "extract", "text"]):
            file = await update.message.photo[-1].get_file()
            await file.download_to_drive("image.jpg")

            try:
                text = pytesseract.image_to_string(Image.open("image.jpg"))
                user_msg = f"Extracted text: {text}"
            except:
                await update.message.reply_text("❌ Couldn't read image")
                return
        else:
            await update.message.reply_text(
                "📸 Image received.\n👉 Add caption like 'read this' to extract text."
            )
            return
    else:
        return

    # -----------------------------
    # EMPTY CHECK
    # -----------------------------
    if not user_msg.strip():
        return

    # -----------------------------
    # MEMORY
    # -----------------------------
    user_memory[user_id].append(f"User: {user_msg}")
    history = "\n".join(user_memory[user_id][-5:])
    prompt = f"{history}\nAI:"

    # -----------------------------
    # 🤖 STREAMING RESPONSE (FAST)
    # -----------------------------
    try:
        response = requests.post(
            OLLAMA_URL,
            json={
                "model": MODEL,
                "prompt": prompt,
                "stream": True,
            },
            stream=True,
            timeout=120,  # ✅ IMPORTANT
        )

        full_text = ""
        msg = await update.message.reply_text("🤖 Thinking...")

        for line in response.iter_lines():
            if line:
                try:
                    chunk = json.loads(line.decode("utf-8"))
                    token = chunk.get("response", "")
                    full_text += token

                    # ⚡ update every few chars
                    if len(full_text) % 40 == 0:
                        await msg.edit_text(full_text)

                except:
                    continue

        # final update
        await msg.edit_text(full_text if full_text else "⚠️ No response")

    except Exception as e:
        print("ERROR:", e)
        await update.message.reply_text("⚠️ AI server not responding.\nRun: ollama serve")
        return

    # -----------------------------
    # SAVE MEMORY
    # -----------------------------
    user_memory[user_id].append(f"AI: {full_text}")

# -----------------------------
# RUN BOT
# -----------------------------
print("🚀 AI Assistant Started...")

app = ApplicationBuilder().token("8505005605:AAHlPDk7fIe_gGFUUiy5Nxwkv_rJF7u-FBE").build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("stop", stop))
app.add_handler(CommandHandler("clear", clear))

app.add_handler(MessageHandler(filters.TEXT, reply))
app.add_handler(MessageHandler(filters.VOICE, reply))
app.add_handler(MessageHandler(filters.PHOTO, reply))

app.run_polling()

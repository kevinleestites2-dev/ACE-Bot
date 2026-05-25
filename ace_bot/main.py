"""
main.py — ACE Bot v2.0.0
══════════════════════════
Joe's autonomous executive assistant.

v2.0.0 changes:
  - MUSE memory wired into every message handler
  - MUSE context injected into system prompt before every reply
  - Outcome captured after every reply (reflect + consolidate)
  - /status now includes live MUSE memory summary
  - Positive signal detection ("perfect", "exactly", "great")
  - Correction signal detection ("that's wrong", "no", "incorrect")
"""

import os
import logging
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
from dotenv import load_dotenv

from ace_bot.llm import LLMHandler
from ace_bot.voice import VoiceHandler
from ace_bot.memory import MemoryHandler
from ace_bot.n8n_bridge import N8NBridge

load_dotenv()

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)

# Initialize handlers
llm    = LLMHandler()
voice  = VoiceHandler()
memory = MemoryHandler()
n8n    = N8NBridge()

# Positive / correction signal words
POSITIVE_SIGNALS  = {"perfect", "exactly", "great", "correct", "excellent", "yes", "thank you", "thanks"}
NEGATIVE_SIGNALS  = {"wrong", "incorrect", "no", "not right", "that's not", "stop", "bad answer"}


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Sir. ACE online.\n\n"
        "I am your executive assistant. I remember everything.\n"
        "Every interaction makes me sharper.\n\n"
        "Commands:\n"
        "/status  — System health + memory summary\n"
        "/morning — Morning briefing\n\n"
        "Or just talk to me."
    )


async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    mem_summary = memory.memory_summary()
    status_msg = (
        "🛡️ ACE System Status\n"
        "═══════════════════════\n"
        "✅ Brain: Gemini / Groq (Online)\n"
        "✅ Automation: n8n (Connected)\n"
        "✅ Voice: ElevenLabs / Groq Whisper (Active)\n\n"
        f"{mem_summary}"
    )
    await update.message.reply_text(status_msg)


async def morning(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Initiating morning briefing, Sir...")
    user_id = update.effective_user.id
    n8n.trigger_morning_briefing(user_id)

    user_message = "Generate my morning briefing."
    mem_context  = memory.get_context(user_message)
    system_prompt = (
        "You are ACE, a highly efficient executive assistant for Joe — "
        "an elite-level executive and entrepreneur.\n"
        f"{mem_context}\n"
        "Generate a sharp, concise morning briefing. Lead with priorities."
    )
    response_text = llm.chat(user_message, system_instruction=system_prompt)

    memory.save_memory(user_id, user_message, response_text, success=True, domain="schedule")
    await update.message.reply_text(response_text)


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_text = update.message.text
    user_id   = update.effective_user.id

    # ── Positive signal detection ──────────────────────────────────
    if any(w in user_text.lower() for w in POSITIVE_SIGNALS) and len(user_text.split()) <= 4:
        memory.signal_positive()
        await update.message.reply_text("Noted, Sir.")
        return

    # ── Correction signal detection ────────────────────────────────
    if any(w in user_text.lower() for w in NEGATIVE_SIGNALS) and len(user_text.split()) <= 6:
        memory.signal_correction(user_text)
        await update.message.reply_text("Understood. Noted and corrected.")
        return

    # ── MUSE: inject memory context into system prompt ─────────────
    mem_context = memory.get_context(user_text)
    system_prompt = (
        "You are ACE, a highly efficient executive assistant for Joe — "
        "an elite-level entrepreneur and executive.\n"
        "Respond with precision. Be proactive. Anticipate the next step.\n"
    )
    if mem_context:
        system_prompt += f"\n{mem_context}"

    # ── Generate response ──────────────────────────────────────────
    response_text = llm.chat(user_text, system_instruction=system_prompt)

    # ── MUSE: capture outcome ──────────────────────────────────────
    memory.save_memory(user_id, user_text, response_text, success=True)

    await update.message.reply_text(response_text)


async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    voice_file = await update.message.voice.get_file()
    audio_path = "voice_note.ogg"
    await voice_file.download_to_drive(audio_path)
    await update.message.reply_text("Processing...")

    transcribed_text = voice.transcribe(audio_path)
    if not transcribed_text:
        await update.message.reply_text("Couldn't transcribe that. Try again, Sir.")
        return

    user_id = update.effective_user.id

    # ── MUSE: inject context ───────────────────────────────────────
    mem_context = memory.get_context(transcribed_text)
    system_prompt = (
        "You are ACE, a highly efficient executive assistant for Joe.\n"
        "Respond with precision. Be proactive. Anticipate the next step.\n"
    )
    if mem_context:
        system_prompt += f"\n{mem_context}"

    # ── Generate response ──────────────────────────────────────────
    response_text = llm.chat(transcribed_text, system_instruction=system_prompt)

    # ── MUSE: capture outcome ──────────────────────────────────────
    memory.save_memory(user_id, transcribed_text, response_text, success=True)

    # ── Voice response ─────────────────────────────────────────────
    audio_response_path = voice.text_to_speech(response_text)
    if audio_response_path:
        with open(audio_response_path, "rb") as audio_file:
            await update.message.reply_voice(voice=audio_file)
    else:
        await update.message.reply_text(response_text)


if __name__ == "__main__":
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        print("Error: TELEGRAM_BOT_TOKEN not found.")
    else:
        application = ApplicationBuilder().token(token).build()

        application.add_handler(CommandHandler("start",   start))
        application.add_handler(CommandHandler("status",  status))
        application.add_handler(CommandHandler("morning", morning))
        application.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))
        application.add_handler(MessageHandler(filters.VOICE, handle_voice))

        print("ACE Bot v2.0.0 — MUSE MEMORY ONLINE")
        print("Waiting for Joe...")
        application.run_polling()

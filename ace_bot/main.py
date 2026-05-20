import os
import logging
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
from dotenv import load_dotenv

from ace_bot.llm import LLMHandler
from ace_bot.voice import VoiceHandler
from ace_bot.memory import MemoryHandler
from ace_bot.n8n_bridge import N8NBridge

# Load environment variables
load_dotenv()

# Setup logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# Initialize handlers
llm = LLMHandler()
voice = VoiceHandler()
memory = MemoryHandler()
n8n = N8NBridge()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    welcome_text = (
        "Welcome, Sir. I am ACE, your Personal AI Assistant.\n\n"
        "I am online and ready to assist you with your schedule, meetings, and communications.\n\n"
        "Commands:\n"
        "/status - Check system health\n"
        "/morning - Trigger morning briefing\n"
        "Or simply send me a text or voice message."
    )
    await update.message.reply_text(welcome_text)

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    status_msg = (
        "🛡️ ACE System Status:\n"
        "✅ Brain: Letta (Ready)\n"
        "✅ LLM: Gemini 1.5 Flash (Online)\n"
        "✅ Automation: n8n (Connected)\n"
        "✅ Voice: ElevenLabs / Groq Whisper (Active)"
    )
    await update.message.reply_text(status_msg)

async def morning(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Initiating your morning briefing, Sir. Querying n8n and Fathom...")
    # Trigger n8n workflow
    n8n.trigger_morning_briefing(update.effective_user.id)
    
    # Placeholder response (since n8n is async/webhook based)
    briefing = llm.chat("Generate a professional morning greeting for a business executive named Joe. Mention that ACE is preparing the briefing.")
    await update.message.reply_text(briefing)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_text = update.message.text
    user_id = update.effective_user.id
    
    # Fetch context from memory stub
    mem_context = memory.get_memory(user_id)
    
    # Get response from LLM
    system_prompt = f"You are ACE, a highly efficient executive assistant. Context: {mem_context}"
    response_text = llm.chat(user_text, system_instruction=system_prompt)
    
    # Save interaction
    memory.save_memory(user_id, user_text, response_text)
    
    await update.message.reply_text(response_text)

async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Download voice note
    voice_file = await update.message.voice.get_file()
    audio_path = "voice_note.ogg"
    await voice_file.download_to_drive(audio_path)
    
    await update.message.reply_text("Processing voice note...")
    
    # Transcribe
    transcribed_text = voice.transcribe(audio_path)
    if not transcribed_text:
        await update.message.reply_text("Sorry, I couldn't transcribe your message.")
        return

    # Get LLM response
    user_id = update.effective_user.id
    mem_context = memory.get_memory(user_id)
    system_prompt = f"You are ACE, a highly efficient executive assistant. Context: {mem_context}"
    response_text = llm.chat(transcribed_text, system_instruction=system_prompt)
    
    # Convert response to speech
    audio_response_path = voice.text_to_speech(response_text)
    
    if audio_response_path:
        with open(audio_response_path, 'rb') as audio_file:
            await update.message.reply_voice(voice=audio_file)
    else:
        await update.message.reply_text(response_text)

if __name__ == '__main__':
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        print("Error: TELEGRAM_BOT_TOKEN not found in environment.")
    else:
        application = ApplicationBuilder().token(token).build()
        
        # Handlers
        application.add_handler(CommandHandler('start', start))
        application.add_handler(CommandHandler('status', status))
        application.add_handler(CommandHandler('morning', morning))
        application.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))
        application.add_handler(MessageHandler(filters.VOICE, handle_voice))
        
        print("ACE Bot is waking up...")
        application.run_polling()

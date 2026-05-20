# ACE Bot: Autonomous Executive Assistant

ACE (Autonomous Command Environment) is a high-performance personal AI assistant designed for business executives. It integrates persistent memory, advanced LLMs, voice processing, and workflow automation.

## The Stack

- **Brain:** [Letta](https://github.com/letta-ai/letta) (self-hosted) + Supabase (Free Tier) for persistent, long-term memory.
- **LLM:** Google Gemini 1.5 Flash (Primary) + Groq Llama 3 (Backup).
- **Automation:** n8n (Self-hosted on Hugging Face Spaces).
- **Voice In:** Groq Whisper (Fast STT).
- **Voice Out:** ElevenLabs (High-quality TTS).
- **Interface:** Telegram (Primary conduit).

## Project Structure

- `ace_bot/main.py`: Telegram bot entry point.
- `ace_bot/llm.py`: Logic for Gemini/Groq orchestration.
- `ace_bot/voice.py`: STT/TTS handling.
- `ace_bot/memory.py`: Letta memory integration stub.
- `ace_bot/n8n_bridge.py`: Webhook integration for automation.

## Setup Instructions

### 1. API Keys & Prerequisites
Gather the following:
- **Telegram:** Create a bot via [@BotFather](https://t.me/BotFather) and get the `TELEGRAM_BOT_TOKEN`.
- **Google AI:** Get a [Gemini API Key](https://aistudio.google.com/).
- **Groq:** Get a [Groq API Key](https://console.groq.com/).
- **ElevenLabs:** Get an [ElevenLabs API Key](https://elevenlabs.io/).
- **Hugging Face:** Create an account to host n8n.

### 2. Deployment on Hugging Face Spaces (n8n)
1. Create a new Space on Hugging Face.
2. Choose **Docker** as the SDK.
3. Use an n8n Docker image (e.g., `n8nio/n8n`).
4. Set up persistent storage if needed, or connect to an external Supabase instance for n8n data.

### 3. Deploying ACE Bot
#### Local / Docker
1. Clone the repo.
2. Copy `.env.example` to `.env` and fill in your keys.
3. Run `docker-compose up -d`.

#### Hugging Face Spaces (ACE Bot)
1. Create a new Space.
2. Choose **Docker**.
3. Upload the contents of this repository.
4. Go to **Settings > Variables and secrets** and add all the keys from `.env.example`.

## Usage
- **/start**: Initialize ACE and see the menu.
- **/status**: Check system health.
- **/morning**: Trigger the morning briefing workflow.
- **Voice Messages**: Send a voice note; ACE will transcribe, process, and reply with audio.
- **Text Messages**: Chat normally for assistant tasks.

## Connecting Letta + Supabase
1. Self-host Letta (e.g., on a VPS or home server).
2. Configure Letta to use Supabase as the vector database/persistence layer.
3. Update `LETTA_URL` and `LETTA_API_KEY` in your `.env`.

---
*Built for the Forgemaster Pantheon.*

import os
from groq import Groq
from elevenlabs import ElevenLabs
from dotenv import load_dotenv
import requests

load_dotenv()

class VoiceHandler:
    def __init__(self):
        self.groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))
        self.el_client = ElevenLabs(api_key=os.getenv("ELEVENLABS_API_KEY"))
        self.voice_id = os.getenv("ELEVENLABS_VOICE_ID", "pNInz6obpg8n9YZpUIjZ") # Default Adam

    def transcribe(self, audio_file_path):
        """Transcribe audio using Groq Whisper"""
        try:
            with open(audio_file_path, "rb") as file:
                transcription = self.groq_client.audio.transcriptions.create(
                    file=(os.path.basename(audio_file_path), file.read()),
                    model="whisper-large-v3",
                )
            return transcription.text
        except Exception as e:
            print(f"Transcription error: {e}")
            return None

    def text_to_speech(self, text, output_path="response.mp3"):
        """Convert text to speech using ElevenLabs"""
        try:
            audio_generator = self.el_client.generate(
                text=text,
                voice=self.voice_id,
                model="eleven_multilingual_v2"
            )
            
            # ElevenLabs generator returns bytes in chunks or full
            with open(output_path, "wb") as f:
                for chunk in audio_generator:
                    f.write(chunk)
            
            return output_path
        except Exception as e:
            print(f"TTS error: {e}")
            return None

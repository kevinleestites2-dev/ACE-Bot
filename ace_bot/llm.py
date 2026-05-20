import os
import google.generativeai as genai
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

class LLMHandler:
    def __init__(self):
        genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
        self.gemini_model = genai.GenerativeModel('gemini-1.5-flash')
        self.groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))
        self.groq_model = os.getenv("GROQ_LLM_MODEL", "llama-3.3-70b-versatile")

    def chat(self, prompt, system_instruction=None):
        try:
            # Primary: Gemini
            if system_instruction:
                # Gemini 1.5 system instructions are handled in model config or prepending
                full_prompt = f"System: {system_instruction}\n\nUser: {prompt}"
            else:
                full_prompt = prompt
            
            response = self.gemini_model.generate_content(full_prompt)
            return response.text
        except Exception as e:
            print(f"Gemini Error, falling back to Groq: {e}")
            try:
                # Backup: Groq
                messages = []
                if system_instruction:
                    messages.append({"role": "system", "content": system_instruction})
                messages.append({"role": "user", "content": prompt})
                
                completion = self.groq_client.chat.completions.create(
                    model=self.groq_model,
                    messages=messages
                )
                return completion.choices[0].message.content
            except Exception as e2:
                return f"Error in both LLM providers: {e2}"

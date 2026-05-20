import os
import requests
from dotenv import load_dotenv

load_dotenv()

class N8NBridge:
    def __init__(self):
        self.webhook_url = os.getenv("N8N_WEBHOOK_URL")

    def trigger_workflow(self, payload):
        """Send data to n8n webhook"""
        if not self.webhook_url:
            print("N8N_WEBHOOK_URL not set.")
            return None
        
        try:
            response = requests.post(self.webhook_url, json=payload)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"n8n trigger error: {e}")
            return None

    def trigger_morning_briefing(self, user_id):
        """Specifically trigger the morning briefing workflow"""
        payload = {
            "action": "morning_briefing",
            "user_id": user_id
        }
        return self.trigger_workflow(payload)

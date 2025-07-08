from google import genai
from google.genai import types
from dotenv import load_dotenv
import os

load_dotenv()

class LLM:
    def __init__(self, system_message: str = ""):
        self.api_key=os.getenv("GEMINI_API_KEY")
        self.system_message = system_message

    def send_message_with_history(self, history: list, message: str, save_history=False) -> str:
        try:
            contents = []

            # Add previous history
            for entry in history:
                contents.append(entry["parts"][0]["text"])

            # Append new user message
            contents.append(message)

            response = genai.Client(api_key= self.api_key).models.generate_content(
                model="gemini-2.5-flash",
                contents=contents,
                config=types.GenerateContentConfig(
                    system_instruction=self.system_message,
                    # Can add: max_output_tokens, temperature, top_p, etc.
                )
            )

            text = response.text

            if save_history:
                self.append_to_history(history, "user", message)
                self.append_to_history(history, "model", text)

            return text

        except Exception as e:
            print(f"Error while sending message: {e}")
            return ""

    def append_to_history(self, history: list, role: str, text: str):
        history.append({"role": role, "parts": [{"text": text}]})

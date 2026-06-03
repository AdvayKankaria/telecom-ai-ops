import os
from google import genai
from dotenv import load_dotenv

load_dotenv()
client = genai.Client()

print("Available models:")
for m in client.models.list():
    if "generateContent" in m.supported_actions and "flash" in m.name:
        print(m.name)

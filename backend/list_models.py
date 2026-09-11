import os
from google import genai
from dotenv import load_dotenv

load_dotenv()
client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))

print("Available models:")
for m in client.models.list():
    if "flash" in m.name or "pro" in m.name:
        print(f"{m.name} - {m.version}")

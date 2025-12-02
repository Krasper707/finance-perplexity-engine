import os
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=os.getenv("OPENROUTER_API_KEY"),
)

print("Sending request to OpenRouter...")

try:
    response = client.chat.completions.create(
        model="openai/gpt-oss-20b:free", 
        messages=[
            {
                "role": "user",
                "content": "How many r's are in the word 'strawberry'?"
            }
        ],
        extra_body={
            "reasoning": {"enabled": True} 
        }
    )

    message = response.choices[0].message

    # 1. Print the Hidden Reasoning (The "Thinking" Part)
    # OpenRouter/DeepSeek often puts this in a special field, sometimes 'reasoning' or inside 'content'
    if hasattr(message, 'reasoning') and message.reasoning:
        print("\n--- [THOUGHT PROCESS] ---")
        print(message.reasoning)
    else:
        print("\n(No specific reasoning field returned, checking provider specific fields...)")

    # 2. Print the Final Answer
    print("\n--- [FINAL ANSWER] ---")
    print(message.content)

except Exception as e:
    print(f"\nError: {e}")
    print("Tip: If the model name is wrong, try 'meta-llama/llama-3.1-8b-instruct:free'")
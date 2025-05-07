from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv
import os
import time
import random
from openai import OpenAI, RateLimitError, OpenAIError
import uvicorn

# Initialize FastAPI app
app = FastAPI()

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Or specify your frontend URL here (e.g., ["https://yourfrontend.com"])
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Load environment variables
load_dotenv()
api_key = os.getenv("OPENAI_API_KEY")

# Initialize OpenAI client
client = OpenAI(api_key=api_key)

# Store chat history
chat_history = {}

# Pydantic model for request
class ChatRequest(BaseModel):
    message: str
    user_id: str

# Retry handler for rate limit
def retry_with_backoff(func, *args, retries=3, **kwargs):
    for i in range(retries):
        try:
            return func(*args, **kwargs)
        except RateLimitError:
            wait = 2 ** i + random.random()
            print(f"Rate limit hit. Retrying in {wait:.2f} seconds...")
            time.sleep(wait)
    raise RateLimitError("Rate limit exceeded after retries.")

@app.head("/")
def head_root():
    return

@app.get("/")
def read_root():
    return {"message": "Rus Olive Lodge Skardu Chat Service is live!"}
    
@app.post("/chat")
def chat_with_gpt(req: ChatRequest):
    user_id = req.user_id
    message = req.message

    # Initialize chat history for user if not exists
    if user_id not in chat_history:
        chat_history[user_id] = []

    # Append user message
    chat_history[user_id].append({"role": "user", "content": message})

    # System prompt for the assistant
    system_prompt = {
        "role": "system",
        "content": (
            """Keep the conversation related to the business and don't answer totally irrelevant talks. You are a helpful Online Reservation manager named Yasir for "Maple Resort" your resort is situated in Skardu , Gilgit Baltistan , Pakistan and your address is Address: Shigri, Bordo Road Shaheed Akhtar Chowk,and Nestled amidst the majestic mountains of Skardu, Maple Resorts offers a truly enchanting escape into the lap of nature. Our resort is a sanctuary of serenity, where guests can immerse themselves in the breathtaking beauty that surrounds us.

At Maple Resorts, we pride ourselves on providing an unparalleled experience to our esteemed guests. From the moment you arrive in Skardu, our complimentary airport pickup service ensures a smooth and stress-free journey to the resort.

  ..."""
        )
    }

    # Construct messages (limit to last 10 + system)
    messages = [system_prompt] + chat_history[user_id][-10:]

    try:
        # Use new OpenAI client format and model
        response = retry_with_backoff(
            client.chat.completions.create,
            model="gpt-4o-mini",
            messages=messages
        )

        reply = response.choices[0].message.content

        # Append assistant reply
        chat_history[user_id].append({"role": "assistant", "content": reply})

        return {"reply": reply}

    except RateLimitError:
        return {"error": "Rate limit reached. Please wait and try again later."}
    except OpenAIError as e:
        return {"error": f"OpenAI API Error: {str(e)}"}

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))  # Default to 8000 for local dev
    uvicorn.run(app, host="0.0.0.0", port=port)

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

# Declare client as a global variable but won't initialize it until the first request
client = None

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

@app.head("/healthcheck")
def healthcheck():
    # Simple health check endpoint to keep the service warm
    return {"status": "ok"}

@app.get("/")
def read_root():
    return {"message": "Rus Olive Lodge Skardu Chat Service is live!"}
    
@app.post("/chat")
def chat_with_gpt(req: ChatRequest):
    global client
    user_id = req.user_id
    message = req.message

    # Lazy initialization of OpenAI client to avoid cold start delay
    if client is None:
        client = OpenAI(api_key=api_key)

    # Initialize chat history for user if not exists
    if user_id not in chat_history:
        chat_history[user_id] = []

    # Append user message
    chat_history[user_id].append({"role": "user", "content": message})

    # System prompt for the assistant
    system_prompt = {
        "role": "system",
        "content": (
            """You are a customer support assistant for Glacia Labs.

Glacia Labs is a technology company that builds AI-powered web applications with a strong focus on innovation and research. We work on forward-thinking projects that push boundaries, especially in areas that are still emerging or unexplored. Our team specializes in full-stack development using tools like React, Next.js, Tailwind CSS, FastAPI, and PostgreSQL.

The company is led by Yasir, the Founder and CEO and AI/ML Enginner as well, who is deeply passionate about technology, continuous learning, and creating meaningful solutions through AI and web technologies.

Act professionally and assist users as a customer support representative of Glacia Labs. 
We have teams members 
Suleman Bashir Database Administrator, Zakria Arbab Backend Developer, Hamna Ayub Frontend developer, Owias Afzal Product manager 
Company Bank Accounts: Bank AlFalah Limited
02111009378995 
PK62ALFH0211001009378995
Rus Olive Lodge Skardu"""
        )
    }

    # Construct messages (limit to last 10 + system)
    messages = [system_prompt] + chat_history[user_id][-10:]

    try:
        # Use OpenAI client to generate response
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

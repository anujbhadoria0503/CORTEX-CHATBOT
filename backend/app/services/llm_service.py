import os
from dotenv import load_dotenv
from groq import Groq
from app.prompts.rag_prompt import (
    SYSTEM_PROMPT,
    build_rag_prompt
)
# LOAD ENVIRONMENT VARIABLES
load_dotenv()
# GROQ CLIENT
client = Groq(
    api_key=os.getenv("GROQ_API_KEY")
)
# ASK GROQ
def ask_groq(
    question: str,
    context: str
):
    # BUILD RAG PROMPT
    prompt = build_rag_prompt(
        context=context,
        question=question
    )
    # SEND REQUEST TO GROQ
    completion = client.chat.completions.create(
        model="qwen/qwen3.8-27b",
        messages=[
            # SYSTEM MESSAGE
            {
                "role": "system",
                "content": SYSTEM_PROMPT
            },
            # USER MESSAGE
            {
                "role": "user",
                "content": prompt
            }
        ],
        temperature=0.7,
        max_tokens=512
    )
    # RETURN ANSWER
    return completion.choices[0].message.content
from fastapi import FastAPI
from app.db.connection import engine
from app.api.routes.ask_conversation import router as ask_conversation
from app.api.routes.uploads import router as upload_router
app = FastAPI(title="Groq Chatbot API")
# Register routers
app.include_router(ask_conversation)
app.include_router(upload_router)
@app.get("/")
def home():
    return {
        "message": "Groq Chatbot API Running"
    }
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app,
        host="127.0.0.1",
        port=8001
    )
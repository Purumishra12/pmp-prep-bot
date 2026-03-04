from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes.topics import router as topics_router
from app.api.routes.chat import router as chat_router
from app.api.routes.quiz import router as quiz_router
from app.api.routes.progress import router as progress_router
from app.api.routes.knowledge import router as knowledge_router

app = FastAPI(title="PMP Prep Bot API", version="0.2.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(topics_router)
app.include_router(chat_router)
app.include_router(quiz_router)
app.include_router(progress_router)
app.include_router(knowledge_router)


@app.get("/api/health")
def health_check():
    return {"status": "ok", "service": "pmp-prep-bot-api"}
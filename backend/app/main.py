from contextlib import asynccontextmanager

from dotenv import load_dotenv

load_dotenv()

import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api.tasks import router as tasks_router
from .api.chat import router as chat_router
from .api.schedule import router as schedule_router
from .database import engine, Base

# CORS: allow localhost for dev; in production set CORS_ORIGINS (comma-separated) e.g. https://yourapp.vercel.app
_cors_origins = os.getenv("CORS_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000").strip().split(",")


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(
    title="FocusFlow API",
    description="AI-powered task command center",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(tasks_router)
app.include_router(chat_router)
app.include_router(schedule_router)


@app.get("/health")
def health():
    return {"status": "ok"}

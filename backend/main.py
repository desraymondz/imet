from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.ai.asr.faster_whisper import get_asr
from backend.ai.embeddings.bge import get_embedder
from backend.db import check_db_connection, init_db

from backend.routers import auth
from backend.routers import captures
from backend.routers import contacts
from backend.routers import recall


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Run during application startup and shutdown."""

    # Check if the database is reachable
    if not check_db_connection():
        raise RuntimeError("Cannot connect to database. Is Postgres running?")
    
    # Initialise the database
    init_db()
    print("iMet: Database initialised successfully")

    # Load the ASR model
    get_asr()
    print("iMet: ASR model loaded successfully")

    # Load the embedding model
    get_embedder()
    print("iMet: Embedding model loaded successfully")

    yield


# Create FastAPI app
app = FastAPI(
    title="iMet API",
    version="0.1.0",
    lifespan=lifespan,
)

# Handle CORS requests from the frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router)
app.include_router(captures.router)
app.include_router(contacts.router)
app.include_router(recall.router)

@app.get("/health")
def health():
    """Health check endpoint to verify the API is running and the database is reachable."""
    return {
        "status": "ok", 
        "db": check_db_connection()
    }
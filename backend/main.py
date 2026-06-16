from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.config import settings
from backend.db import check_db_connection, init_db

from backend.routers import auth


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Run during application startup and shutdown."""

    # Check if the database is reachable
    if not check_db_connection():
        raise RuntimeError("Cannot connect to database. Is Postgres running?")
    
    # Initialise the database
    init_db()
    print("iMet: Database initialised successfully")
    
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

@app.get("/health")
def health():
    """Health check endpoint to verify the API is running and the database is reachable."""
    return {
        "status": "ok", 
        "db": check_db_connection()
    }
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.services.database_service import db
from app.routes.documents import router as documents_router
from app.routes.sessions import router as sessions_router
from app.routes.agent import router as agent_router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("legallens_backend")

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Initializing LegalLens Backend database service...")
    await db.init_db()
    logger.info("LegalLens Backend ready to serve requests.")
    yield
    logger.info("Shutting down LegalLens Backend.")

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="Backend API server for LegalLens Multi-Agent System with Google Cloud Storage and Session DB persistence.",
    lifespan=lifespan
)

# Enable CORS for Frontend development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register API Routers
app.include_router(documents_router, prefix=f"{settings.API_V1_PREFIX}/documents", tags=["Documents"])
app.include_router(sessions_router, prefix=f"{settings.API_V1_PREFIX}/sessions", tags=["Sessions"])
app.include_router(agent_router, prefix=f"{settings.API_V1_PREFIX}/agent", tags=["Agent Execution"])

@app.get("/health", tags=["Health"])
async def health_check():
    return {
        "status": "healthy",
        "app": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "gcp_project": settings.GOOGLE_CLOUD_PROJECT,
        "gcs_bucket": settings.GCS_BUCKET_NAME
    }

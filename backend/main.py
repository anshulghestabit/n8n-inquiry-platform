from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api import auth, system
from app.core.config import get_settings

settings = get_settings()

app = FastAPI(
    title="n8n Inquiry Platform API",
    version="0.1.0",
    docs_url="/docs" if settings.environment == "development" else None
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_url],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(system.router)
app.include_router(auth.router)

@app.get("/health")
async def health():
    return {
        "status": "ok",
        "llm_provider": settings.llm_provider,
        "environment": settings.environment
    }

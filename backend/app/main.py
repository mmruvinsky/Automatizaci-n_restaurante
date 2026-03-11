"""
Aplicación principal de FastAPI.
"""

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from app.core.config import settings
from app.api import reservation, tables, auth, audit

# ── Rate limiter global ───────────────────────────────────────────────────────
limiter = Limiter(key_func=get_remote_address)

# ── Aplicación ────────────────────────────────────────────────────────────────
app = FastAPI(
    title=settings.APP_NAME,
    description="API REST para gestión de reservas de restaurante",
    version="1.0.0"
)

# Adjuntar limiter a la app para que slowapi lo encuentre
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# ── CORS dinámico por ambiente ────────────────────────────────────────────────
# En desarrollo: se permite localhost para facilitar el trabajo local.
# En producción: solo el dominio real del frontend, sin excepciones.
if settings.ENVIRONMENT == "production":
    allowed_origins = [settings.FRONTEND_URL]
else:
    # dev / staging
    allowed_origins = [
        settings.FRONTEND_URL,
        "http://localhost:3000",
        "http://localhost:5173",  # Vite, por si se usa en el futuro
    ]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ───────────────────────────────────────────────────────────────────
app.include_router(reservation.router)
app.include_router(tables.router)
app.include_router(auth.router)
app.include_router(audit.router)


@app.get("/")
def root():
    return {
        "app": settings.APP_NAME,
        "version": "1.0.0",
        "status": "running",
        "environment": settings.ENVIRONMENT,
        "docs": "/docs" if settings.ENVIRONMENT != "production" else "disabled",
    }


@app.get("/health")
def health_check():
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
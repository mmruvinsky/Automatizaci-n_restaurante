"""
Aplicación principal de FastAPI.
Incluye scheduler para resumen de mediodía (12:00) y nocturno (20:30).
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from datetime import date

from app.core.config import settings
from app.api import reservation, tables, auth, audit

# ── Rate limiter ──────────────────────────────────────────────────────────────
limiter = Limiter(key_func=get_remote_address)

# ── App ───────────────────────────────────────────────────────────────────────
app = FastAPI(
    title=settings.APP_NAME,
    description="API REST para gestión de reservas de restaurante",
    version="1.0.0",
    docs_url="/docs" if settings.ENVIRONMENT != "production" else None,
    redoc_url="/redoc" if settings.ENVIRONMENT != "production" else None,
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# ── CORS ──────────────────────────────────────────────────────────────────────
if settings.ENVIRONMENT == "production":
    allowed_origins = [settings.FRONTEND_URL]
else:
    allowed_origins = [
        settings.FRONTEND_URL,
        "http://localhost:3000",
        "http://localhost:5173",
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


# ── Lógica de resumen ─────────────────────────────────────────────────────────

def _send_summary(turno: str) -> None:
    """
    Función base que trae las reservas del día,
    filtra por turno y envía el resumen por WhatsApp.

    turno: "mediodia" → reservas antes de las 20:00
           "noche"    → reservas desde las 20:00
    """
    from app.core.database import SessionLocal
    from app.models import Reservation
    from app.services.whatsapp_service import whatsapp_service

    print(f"📋 Ejecutando resumen de {turno}...")
    db = SessionLocal()
    try:
        today = date.today()
        todas = (
            db.query(Reservation)
            .filter(
                Reservation.date >= f"{today} 00:00:00",
                Reservation.date <= f"{today} 23:59:59",
            )
            .all()
        )

        if turno == "noche":
            filtradas = [r for r in todas if r.time >= "20:00"]
        else:
            filtradas = [r for r in todas if r.time < "20:00"]

        whatsapp_service.send_summary(filtradas, turno=turno)
        print(f"✅ Resumen de {turno} enviado ({len(filtradas)} reservas)")

    except Exception as e:
        print(f"❌ Error en resumen de {turno}: {e}")
    finally:
        db.close()


def send_lunch_summary() -> None:
    _send_summary(turno="mediodia")


def send_nightly_summary() -> None:
    _send_summary(turno="noche")


# ── Scheduler ─────────────────────────────────────────────────────────────────

scheduler = BackgroundScheduler(timezone=settings.TIMEZONE)

scheduler.add_job(
    send_lunch_summary,
    trigger=CronTrigger(hour=12, minute=0, timezone=settings.TIMEZONE),
    id="lunch_summary",
    name="Resumen mediodía 12:00",
    replace_existing=True,
)

scheduler.add_job(
    send_nightly_summary,
    trigger=CronTrigger(hour=20, minute=30, timezone=settings.TIMEZONE),
    id="nightly_summary",
    name="Resumen nocturno 20:30",
    replace_existing=True,
)


@app.on_event("startup")
def startup_event():
    scheduler.start()
    print("✅ Scheduler iniciado")
    print("   ☀️  Resumen mediodía  → 12:00")
    print("   🌙  Resumen nocturno  → 20:30")


@app.on_event("shutdown")
def shutdown_event():
    scheduler.shutdown()
    print("🛑 Scheduler detenido")


# ── Endpoints base ────────────────────────────────────────────────────────────

@app.get("/")
def root():
    return {
        "app": settings.APP_NAME,
        "version": "1.0.0",
        "status": "running",
        "environment": settings.ENVIRONMENT,
    }


@app.get("/health")
def health_check():
    return {"status": "healthy"}


@app.post("/admin/send-lunch-summary-now")
def trigger_lunch_now():
    """Dispara el resumen de mediodía manualmente (para testing)."""
    send_lunch_summary()
    return {"message": "Resumen de mediodía enviado"}


@app.post("/admin/send-nightly-summary-now")
def trigger_nightly_now():
    """Dispara el resumen nocturno manualmente (para testing)."""
    send_nightly_summary()
    return {"message": "Resumen nocturno enviado"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
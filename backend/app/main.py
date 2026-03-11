"""
Aplicación principal de FastAPI.

Este es el punto de entrada de tu API. Aquí se configuran:
- CORS (para conectar con React)
- Rutas/endpoints
- Middleware
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.api import reservation, tables, auth

# Crear aplicación FastAPI
app = FastAPI(
    title=settings.APP_NAME,
    description="API REST para gestión de reservas de restaurante",
    version="1.0.0"
)

# Configurar CORS para permitir requests del frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.FRONTEND_URL, "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],  # Permite GET, POST, PUT, DELETE, etc.
    allow_headers=["*"],  # Permite todos los headers
)

# Incluir routers (endpoints)
app.include_router(reservation.router)  
app.include_router(tables.router)
app.include_router(auth.router)


@app.get("/")
def root():
    """
    Endpoint raíz - muestra info básica de la API.
    """
    return {
        "app": settings.APP_NAME,
        "version": "1.0.0",
        "status": "running",
        "docs": "/docs",  # Documentación interactiva automática
    }


@app.get("/health")
def health_check():
    """
    Health check - útil para verificar que la API está funcionando.
    """
    return {"status": "healthy"}


# Si ejecutas este archivo directamente, arranca el servidor
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
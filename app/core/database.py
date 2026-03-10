"""
Configuración de la conexión a PostgreSQL con SQLAlchemy.

SQLAlchemy es un ORM (Object-Relational Mapping) que nos permite
trabajar con la base de datos usando objetos de Python en lugar de SQL directo.
"""

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from .config import settings

# Motor de base de datos
# echo=True muestra los queries SQL en consola (útil para aprender)
engine = create_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,
    pool_pre_ping=True  # Verifica que la conexión esté activa antes de usarla
)

# SessionLocal es una "fábrica" de sesiones
# Cada sesión es una conversación con la base de datos
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

# Base es la clase padre de todos nuestros modelos
Base = declarative_base()


def get_db():
    """
    Dependency que proporciona una sesión de base de datos.
    FastAPI la usará automáticamente en los endpoints.
    
    Uso:
        @app.get("/reservas")
        def get_reservas(db: Session = Depends(get_db)):
            return db.query(Reservation).all()
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
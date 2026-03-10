"""
Modelo de Mesa (Table).

Este archivo define la estructura de la tabla 'tables' en PostgreSQL.
Cada clase representa una tabla, cada atributo representa una columna.
"""

from sqlalchemy import Column, Integer, String, Boolean
from sqlalchemy.orm import relationship
from app.core.database import Base


class Table(Base):
    """
    Representa una mesa del restaurante.
    
    Atributos:
        id: Identificador único
        name: Nombre de la mesa (ej: "Mesa 1", "Cava")
        capacity: Capacidad máxima de personas
        type: 'standard' o 'cava'
        is_combinable: Si se puede juntar con otras mesas
        is_active: Si la mesa está disponible para usar
    """
    __tablename__ = "tables"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, nullable=False, index=True)
    capacity = Column(Integer, nullable=False)
    type = Column(String, nullable=False, default="standard")  # 'standard' o 'cava'
    is_combinable = Column(Boolean, default=True)
    is_active = Column(Boolean, default=True)
    
    # Relación con reservas (una mesa puede tener muchas reservas)
    # Esta línea crea un atributo virtual 'reservations' que nos permite
    # hacer: mesa.reservations para ver todas las reservas de esa mesa
    reservations = relationship("Reservation", back_populates="table")

    def __repr__(self):
        """Representación en string del objeto (útil para debugging)"""
        return f"<Table {self.name} (cap: {self.capacity}, type: {self.type})>"
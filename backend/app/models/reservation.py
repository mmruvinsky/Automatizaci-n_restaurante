"""
Modelo de Reserva (Reservation).

Este es el modelo principal del sistema. Contiene toda la información
de una reserva y las reglas de negocio asociadas.
"""

from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base


class Reservation(Base):
    """
    Representa una reserva en el restaurante.
    
    Atributos:
        id: Identificador único
        client_id: FK a tabla clients
        table_id: FK a tabla tables (puede ser null si está pendiente)
        date: Fecha de la reserva
        time: Hora de la reserva
        pax: Número de personas
        event_type: 'normal', 'negocios', 'aniversario', 'celebracion'
        requested_cava: Si el cliente pidió la cava
        status: 'confirmed', 'pending', 'cancelled', 'completed'
        special_flag: True si requiere atención especial (5-6 pax)
        notes: Notas de la reserva
        created_at: Timestamp de creación
    """
    __tablename__ = "reservations"

    id = Column(Integer, primary_key=True, index=True)
    
    # Relaciones
    client_id = Column(Integer, ForeignKey("clients.id"), nullable=False)
    table_id = Column(Integer, ForeignKey("tables.id"), nullable=True)
    
    # Información de la reserva
    date = Column(DateTime(timezone=True), nullable=False, index=True)
    time = Column(String, nullable=False)  # Formato: "13:00", "20:30"
    pax = Column(Integer, nullable=False)
    
    # Tipo de evento
    event_type = Column(
        String, 
        default="normal"
    )  # 'normal', 'negocios', 'aniversario', 'celebracion'
    
    requested_cava = Column(Boolean, default=False)
    
    # Estado y flags
    status = Column(
        String, 
        default="pending"
    )  # 'confirmed', 'pending', 'cancelled', 'completed'
    
    special_flag = Column(Boolean, default=False)  # Para reservas 5-6 pax
    
    # Notas y metadata
    notes = Column(Text, nullable=True)
    admin_notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relaciones ORM
    client = relationship("Client", back_populates="reservations")
    table = relationship("Table", back_populates="reservations")

    def __repr__(self):
        return (
            f"<Reservation #{self.id} - {self.client.full_name if self.client else 'N/A'} "
            f"({self.pax} pax, {self.date.strftime('%Y-%m-%d')}, {self.status})>"
        )

    @property
    def is_event_special(self) -> bool:
        """Verifica si el evento es especial (no es 'normal')"""
        return self.event_type in ['negocios', 'aniversario', 'celebracion']

    @property
    def should_auto_confirm(self) -> bool:
        """
        Determina si la reserva debería confirmarse automáticamente.
        
        Reglas:
            - Reservas <= 4 pax: confirmación automática
            - Reservas 5-6 pax: flag especial pero puede confirmarse
            - Reservas > 6 pax: siempre requieren confirmación manual
        """
        return self.pax <= 4

    @property
    def needs_manual_review(self) -> bool:
        """Verifica si necesita revisión manual"""
        return self.pax > 6 or (self.requested_cava and self.status == 'pending')
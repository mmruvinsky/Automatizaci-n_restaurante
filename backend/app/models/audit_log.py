"""
Modelo de AuditLog - Trazabilidad de cambios sobre reservas.

Registra automáticamente cualquier cambio de estado o asignación manual
realizado por el panel admin.
"""

from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base


class AuditLog(Base):
    """
    Registro inmutable de cambios sobre reservas.

    Atributos:
        id: Identificador único
        reservation_id: FK a la reserva afectada
        action: Tipo de acción ('status_change', 'table_assigned', 'cancelled')
        previous_value: Valor anterior (estado o mesa)
        new_value: Valor nuevo
        performed_by: Usuario admin que realizó la acción
        note: Detalle adicional opcional
        created_at: Timestamp del cambio (inmutable)
    """
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    reservation_id = Column(Integer, ForeignKey("reservations.id"), nullable=False, index=True)

    action = Column(String, nullable=False)
    # Valores posibles: 'status_change', 'table_assigned', 'cancelled'

    previous_value = Column(String, nullable=True)
    new_value = Column(String, nullable=False)
    performed_by = Column(String, nullable=False)  # username del admin
    note = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relación (solo lectura, para queries)
    reservation = relationship("Reservation", backref="audit_logs")

    def __repr__(self):
        return (
            f"<AuditLog reservation=#{self.reservation_id} "
            f"action={self.action} by={self.performed_by}>"
        )
"""
Servicio de Auditoría.

Responsabilidad única: escribir y leer registros de cambios.
Se llama desde los endpoints admin después de cada operación exitosa.
"""

from sqlalchemy.orm import Session
from typing import Optional, List

from app.models.audit_log import AuditLog
from app.schemas.audit_log import AuditLogCreate


class AuditService:

    def __init__(self, db: Session):
        self.db = db

    def log(
        self,
        reservation_id: int,
        action: str,
        new_value: str,
        performed_by: str,
        previous_value: Optional[str] = None,
        note: Optional[str] = None,
    ) -> AuditLog:
        """
        Escribe un registro de auditoría.

        Args:
            reservation_id: ID de la reserva afectada
            action: 'status_change' | 'table_assigned' | 'cancelled'
            new_value: Valor nuevo (ej: 'confirmed', 'Mesa 5')
            performed_by: Username del admin que realizó la acción
            previous_value: Valor anterior (puede ser None si no aplica)
            note: Detalle adicional libre
        """
        entry = AuditLog(
            reservation_id=reservation_id,
            action=action,
            previous_value=previous_value,
            new_value=new_value,
            performed_by=performed_by,
            note=note,
        )
        self.db.add(entry)
        self.db.flush()  # Persiste sin commit para que sea atómico con la operación principal
        return entry

    def get_by_reservation(self, reservation_id: int) -> List[AuditLog]:
        """Devuelve todos los logs de una reserva, ordenados por fecha."""
        return (
            self.db.query(AuditLog)
            .filter(AuditLog.reservation_id == reservation_id)
            .order_by(AuditLog.created_at.asc())
            .all()
        )

    def get_recent(self, limit: int = 50, offset: int = 0):
        """Devuelve los últimos N logs del sistema (para el panel admin)."""
        total = self.db.query(AuditLog).count()
        items = (
            self.db.query(AuditLog)
            .order_by(AuditLog.created_at.desc())
            .offset(offset)
            .limit(limit)
            .all()
        )
        return total, items
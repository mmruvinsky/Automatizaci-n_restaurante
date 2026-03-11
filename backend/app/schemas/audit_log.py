"""
Schemas de Pydantic para AuditLog.
"""

from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime


class AuditLogCreate(BaseModel):
    """Schema interno para crear un log (lo usa el servicio, no la API directamente)"""
    reservation_id: int
    action: str
    previous_value: Optional[str] = None
    new_value: str
    performed_by: str
    note: Optional[str] = None


class AuditLogResponse(BaseModel):
    """Schema para respuestas del endpoint de auditoría"""
    id: int
    reservation_id: int
    action: str
    previous_value: Optional[str]
    new_value: str
    performed_by: str
    note: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


class AuditLogListResponse(BaseModel):
    """Lista paginada de logs"""
    total: int
    items: List[AuditLogResponse]
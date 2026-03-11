"""
Endpoints de Auditoría.

Solo accesibles para administradores autenticados.
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import Optional

from app.core.database import get_db
from app.schemas.audit_log import AuditLogListResponse, AuditLogResponse
from app.services.audit_service import AuditService
from app.services.auth_service import require_admin

router = APIRouter(prefix="/audit", tags=["auditoría"])


@router.get("/", response_model=AuditLogListResponse)
def get_audit_logs(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    _=Depends(require_admin),
):
    """
    **Lista los últimos cambios del sistema** (panel admin).

    Devuelve cambios de estado, asignaciones de mesa y cancelaciones,
    ordenados del más reciente al más antiguo.

    Query params:
        - limit: cuántos registros traer (máx 200)
        - offset: para paginación
    """
    service = AuditService(db)
    total, items = service.get_recent(limit=limit, offset=offset)
    return AuditLogListResponse(total=total, items=items)


@router.get("/reservation/{reservation_id}", response_model=AuditLogListResponse)
def get_audit_logs_by_reservation(
    reservation_id: int,
    db: Session = Depends(get_db),
    _=Depends(require_admin),
):
    """
    **Historial de cambios de una reserva específica**.

    Útil para resolver disputas: muestra exactamente qué pasó,
    en qué orden, y quién lo hizo.
    """
    service = AuditService(db)
    items = service.get_by_reservation(reservation_id)
    return AuditLogListResponse(total=len(items), items=items)
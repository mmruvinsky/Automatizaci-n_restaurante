"""
Endpoints de la API para Reservas.
"""

from fastapi import APIRouter, Depends, HTTPException, Request, status as http_status
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import date as date_type
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.core.database import get_db
from app.schemas import ReservationCreate, ReservationResponse, ReservationListItem
from app.schemas.reservation import ReservationStatusUpdate
from app.services.reservation_service import ReservationService, ReservationNotFoundError, TableUnavailableError
from app.services.whatsapp_service import whatsapp_service
from app.services.audit_service import AuditService
from app.models import Reservation
from app.services.auth_service import require_admin
from app.schemas.auth import UserInDB

limiter = Limiter(key_func=get_remote_address)
router = APIRouter(prefix="/reservations", tags=["reservations"])


@router.post("/", response_model=ReservationResponse, status_code=http_status.HTTP_201_CREATED)
@limiter.limit("5/minute;10/hour")
def create_reservation(
    request: Request,
    reservation: ReservationCreate,
    db: Session = Depends(get_db)
):
    """
    **Crea una nueva reserva** (endpoint público — formulario web).

    Rate limit: máximo 5 requests por minuto y 10 por hora por IP.
    """
    service = ReservationService(db)
    new_reservation, message = service.create_reservation(reservation)

    if new_reservation.status == "confirmed":
        whatsapp_service.send_confirmation(new_reservation)
    else:
        whatsapp_service.send_pending_notification(new_reservation)
        whatsapp_service.notify_admin(new_reservation, message)

    if new_reservation.special_flag:
        whatsapp_service.notify_admin(
            new_reservation,
            "Reserva de 5-6 personas - verificar disponibilidad"
        )

    return ReservationResponse(
        id=new_reservation.id,
        client_id=new_reservation.client_id,
        table_id=new_reservation.table_id,
        date=new_reservation.date,
        time=new_reservation.time,
        pax=new_reservation.pax,
        event_type=new_reservation.event_type,
        requested_cava=new_reservation.requested_cava,
        status=new_reservation.status,
        special_flag=new_reservation.special_flag,
        notes=new_reservation.notes,
        admin_notes=new_reservation.admin_notes,
        created_at=new_reservation.created_at,
        client_name=new_reservation.client.full_name if new_reservation.client else None,
        client_phone=new_reservation.client.phone if new_reservation.client else None,
        client_vip_level=new_reservation.client.vip_level if new_reservation.client else None,
        table_name=new_reservation.table.name if new_reservation.table else None
    )


@router.get("/", response_model=List[ReservationListItem])
def list_reservations(
    date: date_type = None,
    status: str = None,
    db: Session = Depends(get_db)
):
    """
    **Lista reservas** con filtros opcionales (panel admin).
    """
    service = ReservationService(db)

    if date:
        reservations = service.get_reservations_by_date(date)
    else:
        query = db.query(Reservation)
        if status:
            query = query.filter(Reservation.status == status)
        reservations = query.all()

    return [
        ReservationListItem(
            id=res.id,
            client_name=res.client.full_name,
            phone=res.client.phone,
            date=res.date.strftime("%Y-%m-%d"),
            time=res.time,
            pax=res.pax,
            status=res.status,
            table_name=res.table.name if res.table else "Sin asignar",
            event_type=res.event_type,
            vip_level=res.client.vip_level,
            requested_cava=res.requested_cava,
            special_flag=res.special_flag
        )
        for res in reservations
    ]


@router.get("/{reservation_id}", response_model=ReservationResponse)
def get_reservation(
    reservation_id: int,
    db: Session = Depends(get_db)
):
    """
    **Obtiene una reserva específica** por ID.
    """
    reservation = db.query(Reservation).filter(Reservation.id == reservation_id).first()
    if not reservation:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail="Reserva no encontrada"
        )

    return ReservationResponse(
        id=reservation.id,
        client_id=reservation.client_id,
        table_id=reservation.table_id,
        date=reservation.date,
        time=reservation.time,
        pax=reservation.pax,
        event_type=reservation.event_type,
        requested_cava=reservation.requested_cava,
        status=reservation.status,
        special_flag=reservation.special_flag,
        notes=reservation.notes,
        admin_notes=reservation.admin_notes,
        created_at=reservation.created_at,
        client_name=reservation.client.full_name,
        client_phone=reservation.client.phone,
        client_vip_level=reservation.client.vip_level,
        table_name=reservation.table.name if reservation.table else None
    )


@router.patch("/{reservation_id}/status")
def update_reservation_status(
    reservation_id: int,
    body: ReservationStatusUpdate,
    db: Session = Depends(get_db),
    current_user: UserInDB = Depends(require_admin)
):
    """
    **Actualiza el estado de una reserva**. Requiere autenticación de administrador.
    """
    service = ReservationService(db)
    audit = AuditService(db)

    try:
        # Capturar estado anterior antes de modificar
        reservation = db.query(Reservation).filter(Reservation.id == reservation_id).first()
        if not reservation:
            raise ReservationNotFoundError()

        previous_status = reservation.status
        previous_table = reservation.table.name if reservation.table else None

        updated = service.update_reservation_status(
            reservation_id=reservation_id,
            status=body.status,
            table_id=body.table_id,
            admin_notes=body.admin_notes
        )

    except ReservationNotFoundError:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail="Reserva no encontrada"
        )
    except TableUnavailableError as e:
        raise HTTPException(
            status_code=http_status.HTTP_409_CONFLICT,
            detail=str(e)
        )

    # Auditar cambio de estado
    if previous_status != body.status:
        audit.log(
            reservation_id=reservation_id,
            action="status_change",
            previous_value=previous_status,
            new_value=body.status,
            performed_by=current_user.username,
            note=body.admin_notes,
        )

    # Auditar asignación de mesa
    if body.table_id is not None:
        new_table_name = updated.table.name if updated.table else str(body.table_id)
        audit.log(
            reservation_id=reservation_id,
            action="table_assigned",
            previous_value=previous_table,
            new_value=new_table_name,
            performed_by=current_user.username,
        )

    db.commit()

    if body.status == "confirmed":
        whatsapp_service.send_confirmation(updated)

    return {"message": "Reserva actualizada", "reservation_id": reservation_id}


@router.delete("/{reservation_id}")
def cancel_reservation(
    reservation_id: int,
    db: Session = Depends(get_db),
    current_user: UserInDB = Depends(require_admin)
):
    """
    **Cancela una reserva**. Requiere autenticación de administrador.
    """
    reservation = db.query(Reservation).filter(Reservation.id == reservation_id).first()
    if not reservation:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail="Reserva no encontrada"
        )

    previous_status = reservation.status
    reservation.status = "cancelled"

    audit = AuditService(db)
    audit.log(
        reservation_id=reservation_id,
        action="cancelled",
        previous_value=previous_status,
        new_value="cancelled",
        performed_by=current_user.username,
    )

    db.commit()
    return {"message": "Reserva cancelada", "reservation_id": reservation_id}
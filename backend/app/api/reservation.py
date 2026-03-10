"""
Endpoints de la API para Reservas.

Estos son los puntos de entrada HTTP que el frontend usará.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from datetime import date

from app.core.database import get_db
from app.schemas import ReservationCreate, ReservationResponse, ReservationListItem
from app.services.reservation_service import ReservationService
from app.services.whatsapp_service import whatsapp_service
from app.models import Reservation

router = APIRouter(prefix="/reservations", tags=["reservations"])


@router.post("/", response_model=ReservationResponse, status_code=status.HTTP_201_CREATED)
def create_reservation(
    reservation: ReservationCreate,
    db: Session = Depends(get_db)
):
    """
    **Crea una nueva reserva** (endpoint público - formulario web).
    
    El sistema aplica automáticamente:
    - Busca o crea el cliente
    - Aplica reglas de negocio
    - Asigna mesa si es posible
    - Actualiza nivel VIP
    - Envía notificaciones
    
    Returns:
        Reserva creada con su estado (confirmed/pending)
    """
    try:
        # Crear reserva con toda la lógica de negocio
        service = ReservationService(db)
        new_reservation, message = service.create_reservation(reservation)
        
        # Enviar notificaciones según el estado
        if new_reservation.status == "confirmed":
            # Reserva confirmada → notificar cliente
            whatsapp_service.send_confirmation(new_reservation)
        else:
            # Reserva pendiente → notificar cliente y admin
            whatsapp_service.send_pending_notification(new_reservation)
            whatsapp_service.notify_admin(new_reservation, message)
        
        # Si es un caso especial (5-6 pax), notificar admin
        if new_reservation.special_flag:
            whatsapp_service.notify_admin(
                new_reservation, 
                "Reserva de 5-6 personas - verificar disponibilidad"
            )
        
        # Preparar respuesta con datos relacionados
        response = ReservationResponse(
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
        
        return response
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Error al crear reserva: {str(e)}"
        )


@router.get("/", response_model=List[ReservationListItem])
def list_reservations(
    date: date = None,
    status: str = None,
    db: Session = Depends(get_db)
):
    """
    **Lista reservas** con filtros opcionales (panel admin).
    
    Query params:
        - date: Filtrar por fecha específica
        - status: Filtrar por estado (confirmed/pending/cancelled)
    """
    query = db.query(Reservation)
    
    # Aplicar filtros
    if date:
        service = ReservationService(db)
        reservations = service.get_reservations_by_date(date)
    else:
        if status:
            query = query.filter(Reservation.status == status)
        reservations = query.all()
    
    # Mapear a schema de respuesta
    result = []
    for res in reservations:
        result.append(ReservationListItem(
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
        ))
    
    return result


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
            status_code=status.HTTP_404_NOT_FOUND,
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
    status: str,
    table_id: int = None,
    admin_notes: str = None,
    db: Session = Depends(get_db)
):
    """
    **Actualiza el estado de una reserva** (panel admin).
    
    Body:
        - status: 'confirmed', 'pending', 'cancelled', 'completed'
        - table_id: (opcional) Asignar mesa
        - admin_notes: (opcional) Notas internas
    """
    try:
        service = ReservationService(db)
        updated_reservation = service.update_reservation_status(
            reservation_id=reservation_id,
            status=status,
            table_id=table_id,
            admin_notes=admin_notes
        )
        
        # Si se confirmó, enviar notificación
        if status == "confirmed":
            whatsapp_service.send_confirmation(updated_reservation)
        
        return {"message": "Reserva actualizada", "reservation_id": reservation_id}
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Error actualizando reserva: {str(e)}"
        )


@router.delete("/{reservation_id}")
def cancel_reservation(
    reservation_id: int,
    db: Session = Depends(get_db)
):
    """
    **Cancela una reserva** (cambia estado a cancelled).
    """
    reservation = db.query(Reservation).filter(Reservation.id == reservation_id).first()
    
    if not reservation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Reserva no encontrada"
        )
    
    reservation.status = "cancelled"
    db.commit()
    
    return {"message": "Reserva cancelada", "reservation_id": reservation_id}
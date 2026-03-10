"""
Schemas de Pydantic para Reserva.
"""

from pydantic import BaseModel, Field, validator
from typing import Optional
from datetime import datetime, date, time


class ReservationBase(BaseModel):
    """Schema base con campos comunes"""
    pax: int = Field(..., gt=0, le=20, description="Número de personas (máx 20)")
    event_type: str = Field(
        default="normal",
        description="Tipo: normal, negocios, aniversario, celebracion"
    )
    requested_cava: bool = Field(default=False, description="¿Solicita la cava?")
    notes: Optional[str] = Field(None, max_length=500, description="Notas del cliente")
    
    @validator('event_type')
    def validate_event_type(cls, v):
        """Valida que el tipo de evento sea válido"""
        valid_types = ['normal', 'negocios', 'aniversario', 'celebracion']
        if v not in valid_types:
            raise ValueError(f'event_type debe ser uno de: {", ".join(valid_types)}')
        return v


class ReservationCreate(ReservationBase):
    """
    Schema para crear una reserva desde el formulario público.
    El cliente proporciona sus datos y los detalles de la reserva.
    """
    # Datos del cliente
    customer_name: str = Field(..., min_length=2, max_length=100)
    customer_phone: str = Field(..., pattern=r'^\+?[0-9]{10,15}$')
    customer_email: Optional[str] = None
    
    # Datos de la reserva
    date: date = Field(..., description="Fecha de la reserva (YYYY-MM-DD)")
    time: str = Field(..., pattern=r'^([01][0-9]|2[0-3]):[0-5][0-9]$', description="Hora (HH:MM)")
    
    @validator('date')
    def validate_date(cls, v):
        """Valida que la fecha no sea en el pasado"""
        if v < date.today():
            raise ValueError('No se pueden hacer reservas en fechas pasadas')
        return v
    
    @validator('time')
    def validate_time(cls, v):
        """Valida que la hora esté en los rangos permitidos"""
        hour, minute = map(int, v.split(':'))
        time_obj = time(hour, minute)
        
        # Horarios permitidos: 12:30-15:00 y 20:30-23:30
        lunch_start = time(12, 30)
        lunch_end = time(15, 0)
        dinner_start = time(20, 30)
        dinner_end = time(23, 30)
        
        if not ((lunch_start <= time_obj <= lunch_end) or (dinner_start <= time_obj <= dinner_end)):
            raise ValueError(
                'Horarios permitidos: 12:30-15:00 (almuerzo) o 20:30-23:30 (cena)'
            )
        return v


class ReservationUpdate(BaseModel):
    """Schema para actualizar una reserva (solo admin)"""
    pax: Optional[int] = Field(None, gt=0, le=20)
    date: Optional[date] = None
    time: Optional[str] = None
    event_type: Optional[str] = None
    requested_cava: Optional[bool] = None
    status: Optional[str] = None
    table_id: Optional[int] = None
    special_flag: Optional[bool] = None
    admin_notes: Optional[str] = None
    
    @validator('status')
    def validate_status(cls, v):
        if v is not None:
            valid_statuses = ['confirmed', 'pending', 'cancelled', 'completed']
            if v not in valid_statuses:
                raise ValueError(f'status debe ser uno de: {", ".join(valid_statuses)}')
        return v


class ReservationResponse(ReservationBase):
    """Schema para respuestas de la API"""
    id: int
    client_id: int
    table_id: Optional[int]
    date: datetime
    time: str
    status: str
    special_flag: bool
    admin_notes: Optional[str]
    created_at: datetime
    
    # Datos del cliente (nested)
    client_name: Optional[str] = None
    client_phone: Optional[str] = None
    client_vip_level: Optional[str] = None
    
    # Datos de la mesa (nested)
    table_name: Optional[str] = None
    
    class Config:
        from_attributes = True


class ReservationListItem(BaseModel):
    """Schema simplificado para listados de reservas"""
    id: int
    client_name: str
    phone: str
    date: str
    time: str
    pax: int
    status: str
    table_name: Optional[str]
    event_type: str
    vip_level: str
    requested_cava: bool
    special_flag: bool
    
    class Config:
        from_attributes = True
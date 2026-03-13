"""
Schemas de Pydantic para Reserva.

Reglas de grupo:
  > 4  personas → mesa especial + aviso a cocina
  > 15 personas → delegado a encargado humano
"""

from pydantic import BaseModel, Field, validator
from typing import Optional
from datetime import datetime
from datetime import date as dt_date
from datetime import time as dt_time


class ReservationBase(BaseModel):
    pax: int = Field(..., gt=0, description="Número de personas (sin límite)")
    event_type: str = Field(default="normal")
    requested_cava: bool = Field(default=False)
    notes: Optional[str] = Field(None, max_length=500)

    @validator('event_type')
    def validate_event_type(cls, v):
        valid_types = ['normal', 'negocios', 'aniversario', 'celebracion']
        if v not in valid_types:
            raise ValueError(f'event_type debe ser uno de: {", ".join(valid_types)}')
        return v


class ReservationCreate(ReservationBase):
    customer_name: str = Field(..., min_length=2, max_length=100)
    customer_phone: str = Field(..., pattern=r'^\+?[0-9]{10,15}$')
    customer_email: Optional[str] = None
    date: dt_date = Field(..., description="Fecha (YYYY-MM-DD)")
    time: str = Field(..., pattern=r'^([01][0-9]|2[0-3]):[0-5][0-9]$')

    @validator('date')
    def validate_date(cls, v):
        if v < dt_date.today():
            raise ValueError('No se pueden hacer reservas en fechas pasadas')
        return v

    @validator('time')
    def validate_time(cls, v):
        hour, minute = map(int, v.split(':'))
        time_obj = dt_time(hour, minute)
        lunch_start, lunch_end = dt_time(12, 30), dt_time(15, 0)
        dinner_start, dinner_end = dt_time(20, 30), dt_time(23, 30)
        if not ((lunch_start <= time_obj <= lunch_end) or (dinner_start <= time_obj <= dinner_end)):
            raise ValueError('Horarios: 12:30-15:00 o 20:30-23:30')
        return v


class ReservationUpdate(BaseModel):
    pax: Optional[int] = Field(None, gt=0)
    date: Optional[dt_date] = None
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


class ReservationStatusUpdate(BaseModel):
    status: str
    table_id: Optional[int] = None
    admin_notes: Optional[str] = None

    @validator('status')
    def validate_status(cls, v):
        valid_statuses = ['confirmed', 'pending', 'cancelled', 'completed']
        if v not in valid_statuses:
            raise ValueError(f'status debe ser uno de: {", ".join(valid_statuses)}')
        return v


class ReservationResponse(ReservationBase):
    id: int
    client_id: int
    table_id: Optional[int]
    date: datetime
    time: str
    status: str
    special_flag: bool
    admin_notes: Optional[str]
    created_at: datetime
    client_name: Optional[str] = None
    client_phone: Optional[str] = None
    client_vip_level: Optional[str] = None
    table_name: Optional[str] = None

    class Config:
        from_attributes = True


class ReservationListItem(BaseModel):
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
"""
Schemas de Pydantic para Cliente.
"""

from pydantic import BaseModel, Field, EmailStr
from typing import Optional
from datetime import datetime


class ClientBase(BaseModel):
    """Schema base con campos comunes"""
    full_name: str = Field(..., min_length=2, description="Nombre completo")
    phone: str = Field(..., pattern=r'^\+?[0-9]{10,15}$', description="Teléfono con código de área")
    email: Optional[EmailStr] = Field(None, description="Email opcional")


class ClientCreate(ClientBase):
    """Schema para crear un cliente nuevo"""
    notes: Optional[str] = None


class ClientUpdate(BaseModel):
    """Schema para actualizar un cliente"""
    full_name: Optional[str] = Field(None, min_length=2)
    phone: Optional[str] = Field(None, pattern=r'^\+?[0-9]{10,15}$')
    email: Optional[EmailStr] = None
    notes: Optional[str] = None


class ClientResponse(ClientBase):
    """Schema para respuestas de la API"""
    id: int
    created_at: datetime
    last_visit_at: datetime
    total_reservations: int
    vip_level: str
    notes: Optional[str] = None
    
    class Config:
        from_attributes = True


class ClientSearchResult(BaseModel):
    """Schema para resultados de búsqueda de cliente"""
    id: int
    full_name: str
    phone: str
    vip_level: str
    total_reservations: int
    last_visit_at: datetime
    
    class Config:
        from_attributes = True
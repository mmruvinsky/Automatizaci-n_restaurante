"""
Schemas de Pydantic para Mesa.

Los schemas definen la estructura de datos que aceptamos/retornamos en la API.
Pydantic valida automáticamente los datos y muestra errores claros.
"""

from pydantic import BaseModel, Field
from typing import Optional


class TableBase(BaseModel):
    """Schema base con campos comunes"""
    name: str = Field(..., description="Nombre de la mesa")
    capacity: int = Field(..., gt=0, description="Capacidad de personas")
    type: str = Field(default="standard", description="'standard' o 'cava'")
    is_combinable: bool = Field(default=True)
    is_active: bool = Field(default=True)


class TableCreate(TableBase):
    """Schema para crear una mesa nueva"""
    pass


class TableUpdate(BaseModel):
    """Schema para actualizar una mesa (todos los campos son opcionales)"""
    name: Optional[str] = None
    capacity: Optional[int] = Field(None, gt=0)
    type: Optional[str] = None
    is_combinable: Optional[bool] = None
    is_active: Optional[bool] = None


class TableResponse(TableBase):
    """
    Schema para respuestas de la API.
    Incluye el ID que viene de la base de datos.
    """
    id: int
    
    class Config:
        # Permite que Pydantic lea datos de objetos SQLAlchemy
        from_attributes = True


class TableAvailability(BaseModel):
    """Schema para consultar disponibilidad de mesas"""
    table_id: int
    table_name: str
    capacity: int
    type: str
    is_available: bool
    reserved_at: Optional[str] = None
"""
Schemas de autenticación.

Estos schemas definen la estructura de datos para login y tokens JWT.
"""

from pydantic import BaseModel, Field
from typing import Optional


class LoginRequest(BaseModel):
    """
    Schema para el request de login.
    El admin envía usuario y contraseña.
    """
    username: str = Field(..., min_length=3, description="Nombre de usuario")
    password: str = Field(..., min_length=6, description="Contraseña")


class Token(BaseModel):
    """
    Schema para la respuesta del login exitoso.
    Devuelve el access token JWT.
    """
    access_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    """
    Schema para los datos decodificados del token.
    Esto es lo que extraemos del JWT al validarlo.
    """
    username: Optional[str] = None
    role: Optional[str] = None  # 'admin' o 'public'


class UserInDB(BaseModel):
    """
    Schema para representar un usuario en la base de datos.
    Por ahora es simple, en el futuro puede expandirse.
    """
    username: str
    hashed_password: str
    role: str = "admin"
    is_active: bool = True
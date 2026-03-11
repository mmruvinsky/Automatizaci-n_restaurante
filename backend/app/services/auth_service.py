"""
Servicio de Autenticación - JWT y seguridad.

Este servicio maneja:
- Generación de tokens JWT
- Validación de tokens
- Hash de contraseñas usando bcrypt nativo
- Verificación de credenciales
"""

from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
import bcrypt 
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from app.core.config import settings
from app.schemas.auth import TokenData, UserInDB

# HTTPBearer es el esquema de autenticación
# Extrae el token del header "Authorization: Bearer <token>"
security = HTTPBearer()

# Algoritmo para firmar el JWT
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 24 horas


# ============================================
# USUARIOS HARDCODEADOS (temporal)
# ============================================
FAKE_USERS_DB = {
    "admin": UserInDB(
        username="admin",
        # Password: "admin123" (hasheado)
        hashed_password="$2b$12$FKs3UVZPS3U3WaGLdbDvSO5BlcBZ9DY7ofQsbofU61sPasYHwXk.K",
        role="admin",
        is_active=True
    )
}


# ============================================
# FUNCIONES DE HASH Y VERIFICACIÓN
# ============================================

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verifica que una contraseña en texto plano coincida con su hash.
    Bcrypt requiere trabajar con bytes, por lo que codificamos los strings a utf-8.
    """
    password_bytes = plain_password.encode('utf-8')
    hash_bytes = hashed_password.encode('utf-8')
    
    try:
        return bcrypt.checkpw(password_bytes, hash_bytes)
    except ValueError:
        # Retorna False si el formato del hash es inválido o está corrupto
        return False


def get_password_hash(password: str) -> str:
    """
    Genera el hash de una contraseña usando bcrypt puro.
    """
    password_bytes = password.encode('utf-8')
    salt = bcrypt.gensalt()
    hashed_bytes = bcrypt.hashpw(password_bytes, salt)
    
    # Decodificamos de vuelta a string para poder guardarlo fácilmente en la BD
    return hashed_bytes.decode('utf-8')


# ============================================
# AUTENTICACIÓN DE USUARIOS
# ============================================

def authenticate_user(username: str, password: str) -> Optional[UserInDB]:
    """
    Autentica un usuario verificando sus credenciales.
    """
    # Buscar usuario en la "base de datos"
    user = FAKE_USERS_DB.get(username)
    
    if not user:
        return None
    
    # Verificar contraseña
    if not verify_password(password, user.hashed_password):
        return None
    
    return user


# ============================================
# GENERACIÓN Y VALIDACIÓN DE TOKENS JWT
# ============================================

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    Crea un token JWT.
    """
    to_encode = data.copy()
    
    # Calcular expiración
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    # Agregar expiración al payload
    to_encode.update({"exp": expire})
    
    # Firmar el token con la SECRET_KEY
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=ALGORITHM)
    
    return encoded_jwt


def decode_token(token: str) -> TokenData:
    """
    Decodifica y valida un token JWT.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="No se pudo validar las credenciales",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        # Decodificar el token
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        role: str = payload.get("role")
        
        if username is None:
            raise credentials_exception
        
        token_data = TokenData(username=username, role=role)
        return token_data
        
    except JWTError:
        raise credentials_exception


# ============================================
# DEPENDENCIES PARA FASTAPI
# ============================================

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> UserInDB:
    """
    Dependency que extrae y valida el usuario actual desde el token JWT.
    """
    # Extraer token del header
    token = credentials.credentials
    
    # Decodificar token
    token_data = decode_token(token)
    
    # Buscar usuario
    user = FAKE_USERS_DB.get(token_data.username)
    
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuario no encontrado"
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Usuario inactivo"
        )
    
    return user


async def require_admin(
    current_user: UserInDB = Depends(get_current_user)
) -> UserInDB:
    """
    Dependency que requiere que el usuario sea admin.
    """
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes permisos de administrador"
        )
    
    return current_user


# ============================================
# UTILIDADES
# ============================================

def generate_password_hash(password: str) -> None:
    """
    Utilidad para generar el hash de una contraseña.
    """
    hashed = get_password_hash(password)
    print(f"\nContraseña: {password}")
    print(f"Hash: {hashed}\n")
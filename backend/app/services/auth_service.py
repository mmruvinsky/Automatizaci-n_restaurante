"""
Servicio de Autenticación - JWT y seguridad.

Este servicio maneja:
- Generación de tokens JWT
- Validación de tokens
- Hash de contraseñas
- Verificación de credenciales
"""

from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from app.core.config import settings
from app.schemas.auth import TokenData, UserInDB

# Configuración de seguridad
# CryptContext maneja el hash de contraseñas usando bcrypt
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# HTTPBearer es el esquema de autenticación
# Extrae el token del header "Authorization: Bearer <token>"
security = HTTPBearer()

# Algoritmo para firmar el JWT
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 24 horas


# ============================================
# USUARIOS HARDCODEADOS (temporal)
# ============================================
# En el futuro, estos estarán en PostgreSQL
# Por ahora, definimos un admin por defecto

FAKE_USERS_DB = {
    "admin": UserInDB(
        username="admin",
        # Password: "admin123" (hasheado)
        hashed_password="$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5GyYPQKKWIB/u",
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
    
    Args:
        plain_password: Contraseña que el usuario ingresa
        hashed_password: Hash almacenado en la BD
        
    Returns:
        True si coinciden, False si no
    """
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """
    Genera el hash de una contraseña.
    
    NUNCA almacenes contraseñas en texto plano.
    Siempre usa hash + salt (bcrypt lo hace automáticamente).
    
    Args:
        password: Contraseña en texto plano
        
    Returns:
        Hash de la contraseña
    """
    return pwd_context.hash(password)


# ============================================
# AUTENTICACIÓN DE USUARIOS
# ============================================

def authenticate_user(username: str, password: str) -> Optional[UserInDB]:
    """
    Autentica un usuario verificando sus credenciales.
    
    Args:
        username: Nombre de usuario
        password: Contraseña en texto plano
        
    Returns:
        UserInDB si las credenciales son correctas, None si no
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
    
    El token contiene:
    - username: identificador del usuario
    - role: rol del usuario (admin, public, etc.)
    - exp: timestamp de expiración
    
    Args:
        data: Diccionario con datos a incluir en el token
        expires_delta: Tiempo de expiración (opcional)
        
    Returns:
        Token JWT como string
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
    
    Args:
        token: Token JWT a decodificar
        
    Returns:
        TokenData con los datos del token
        
    Raises:
        HTTPException: Si el token es inválido o expiró
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
    
    Se usa en endpoints así:
        @app.get("/admin/reservations")
        def get_reservations(current_user: UserInDB = Depends(get_current_user)):
            # current_user contiene los datos del usuario autenticado
            ...
    
    Args:
        credentials: Token extraído del header Authorization
        
    Returns:
        UserInDB del usuario autenticado
        
    Raises:
        HTTPException: Si el token es inválido o el usuario no existe
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
    
    Se usa en endpoints administrativos:
        @app.delete("/tables/{id}")
        def delete_table(
            id: int, 
            admin: UserInDB = Depends(require_admin)
        ):
            # Solo los admins pueden llegar aquí
            ...
    
    Args:
        current_user: Usuario autenticado
        
    Returns:
        UserInDB si es admin
        
    Raises:
        HTTPException: Si el usuario no es admin
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
    
    Uso:
        from app.services.auth_service import generate_password_hash
        generate_password_hash("mi_nueva_contraseña")
    """
    hashed = get_password_hash(password)
    print(f"\nContraseña: {password}")
    print(f"Hash: {hashed}\n")


# Para generar el hash de "admin123":
# generate_password_hash("admin123")
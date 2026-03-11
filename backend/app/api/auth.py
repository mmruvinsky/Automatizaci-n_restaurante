"""
Endpoints de autenticación.

Este archivo contiene los endpoints para:
- Login (obtener token JWT)
- Verificación de token
"""

from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, status

from app.schemas.auth import LoginRequest, Token, UserInDB
from app.services.auth_service import (
    authenticate_user,
    create_access_token,
    get_current_user,
    ACCESS_TOKEN_EXPIRE_MINUTES
)

router = APIRouter(prefix="/auth", tags=["autenticación"])


@router.post("/login", response_model=Token)
def login(credentials: LoginRequest):
    """
    **Endpoint de login** - Autentica al admin y devuelve un token JWT.
    
    **Credenciales por defecto:**
    - Username: `admin`
    - Password: `admin123`
    
    **Flujo:**
    1. El admin envía usuario y contraseña
    2. El backend verifica las credenciales
    3. Si son correctas, genera un JWT
    4. El frontend guarda el token
    5. El frontend envía el token en cada request: `Authorization: Bearer <token>`
    
    **Ejemplo de uso:**
    ```bash
    curl -X POST http://localhost:8000/auth/login \
      -H "Content-Type: application/json" \
      -d '{"username": "admin", "password": "admin123"}'
    ```
    
    **Respuesta:**
    ```json
    {
      "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
      "token_type": "bearer"
    }
    ```
    
    Returns:
        Token JWT válido por 24 horas
    """
    # Autenticar usuario
    user = authenticate_user(credentials.username, credentials.password)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuario o contraseña incorrectos",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Crear token JWT
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username, "role": user.role},
        expires_delta=access_token_expires
    )
    
    return Token(access_token=access_token, token_type="bearer")


@router.get("/me", response_model=UserInDB)
def get_me(current_user: UserInDB = Depends(get_current_user)):
    """
    **Verifica el token actual** y devuelve los datos del usuario.
    
    Este endpoint es útil para:
    - Verificar si el token sigue siendo válido
    - Obtener los datos del usuario autenticado
    - Mostrar info del admin en el frontend
    
    **Requiere autenticación:** Sí (enviar token JWT en el header)
    
    **Ejemplo:**
    ```bash
    curl -X GET http://localhost:8000/auth/me \
      -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
    ```
    
    Returns:
        Datos del usuario autenticado
    """
    return current_user


@router.post("/test-protected")
def test_protected_endpoint(current_user: UserInDB = Depends(get_current_user)):
    """
    **Endpoint de prueba** para verificar que la autenticación funciona.
    
    Este endpoint solo es accesible con un token válido.
    Úsalo para probar que el sistema de autenticación está funcionando.
    
    Returns:
        Mensaje de confirmación con los datos del usuario
    """
    return {
        "message": "¡Autenticación exitosa!",
        "user": current_user.username,
        "role": current_user.role
    }
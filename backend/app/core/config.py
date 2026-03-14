"""
Configuración centralizada de la aplicación.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional
import pytz


class Settings(BaseSettings):

    # Base de datos
    DATABASE_URL: str

    # Aplicación
    APP_NAME: str = "Sistema de Reservas Jamonería"
    DEBUG: bool = True
    SECRET_KEY: str

    # Ambiente: 'development' | 'staging' | 'production'
    # Controla CORS, docs visibles, logs, etc.
    ENVIRONMENT: str = "development"

    # Zona horaria
    TIMEZONE: str = "America/Argentina/Mendoza"

    # Twilio WhatsApp
    TWILIO_ACCOUNT_SID: Optional[str] = None
    TWILIO_AUTH_TOKEN: Optional[str] = None
    TWILIO_WHATSAPP_FROM: Optional[str] = None
    ADMIN_WHATSAPP: Optional[str] = None
    CHEF_WHATSAPP: Optional[str] = None
    OWNER_WHATSAPP: Optional[str] = None

    # CORS — URL del frontend desplegado
    # En desarrollo puede ser http://localhost:3000
    # En producción debe ser el dominio real: https://reservas.jamoneria.com
    FRONTEND_URL: str = "http://localhost:3000"

    # Configuración del negocio
    MAX_CAPACITY: int = 60
    CAVA_TABLE_ID: int = 1
    DEFAULT_MEAL_DURATION: int = 180  # minutos

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=False)

    def get_timezone(self):
        return pytz.timezone(self.TIMEZONE)


settings = Settings()
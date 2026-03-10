"""
Configuración centralizada de la aplicación.
Este archivo lee las variables de entorno del archivo .env
"""

from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional
import pytz


class Settings(BaseSettings):
    """
    Clase que contiene toda la configuración de la app.
    Pydantic automáticamente lee del archivo .env
    """
    
    # Base de datos
    DATABASE_URL: str
    
    # Aplicación
    APP_NAME: str = "Sistema de Reservas Jamonería"
    DEBUG: bool = True
    SECRET_KEY: str
    
    # Zona horaria
    TIMEZONE: str = "America/Argentina/Mendoza"
    
    # Twilio WhatsApp
    TWILIO_ACCOUNT_SID: Optional[str] = None
    TWILIO_AUTH_TOKEN: Optional[str] = None
    TWILIO_WHATSAPP_FROM: Optional[str] = None
    ADMIN_WHATSAPP: Optional[str] = None
    
    # CORS
    FRONTEND_URL: str = "http://localhost:3000"
    
    # Configuración del negocio
    MAX_CAPACITY: int = 60
    CAVA_TABLE_ID: int = 1
    DEFAULT_MEAL_DURATION: int = 180  # minutos
    
    # NUEVA SINTAXIS PARA PYDANTIC V2
    model_config = SettingsConfigDict(env_file=".env", case_sensitive=False)

    def get_timezone(self):
        """Retorna el objeto timezone configurado"""
        return pytz.timezone(self.TIMEZONE)


# Instancia global de configuración
settings = Settings()
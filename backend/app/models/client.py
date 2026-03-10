"""
Modelo de Cliente (Client) - Mini CRM.

Este modelo registra el historial de clientes para fidelización
y asignación estratégica de la cava para clientes VIP.
"""

from sqlalchemy import Column, Integer, String, DateTime, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base


class Client(Base):
    """
    Representa un cliente del restaurante.
    
    Atributos:
        id: Identificador único (UUID en string)
        full_name: Nombre completo
        phone: Teléfono (único, clave para identificar)
        email: Email opcional
        created_at: Fecha de primera visita
        last_visit_at: Fecha de última visita
        total_reservations: Contador de reservas
        vip_level: 'normal', 'frecuente', 'vip'
        notes: Notas internas sobre el cliente
    """
    __tablename__ = "clients"

    id = Column(Integer, primary_key=True, index=True)
    full_name = Column(String, nullable=False)
    phone = Column(String, unique=True, nullable=False, index=True)
    email = Column(String, nullable=True)
    
    # Timestamps automáticos
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    last_visit_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    total_reservations = Column(Integer, default=0)
    vip_level = Column(String, default="normal")  # 'normal', 'frecuente', 'vip'
    notes = Column(Text, nullable=True)
    
    # Relación con reservas
    reservations = relationship("Reservation", back_populates="client")

    def update_vip_level(self):
        """
        Actualiza automáticamente el nivel VIP según número de reservas.
        
        Reglas:
            >= 15 reservas → VIP
            >= 5 reservas → Frecuente  
            < 5 reservas → Normal
        """
        if self.total_reservations >= 15:
            self.vip_level = "vip"
        elif self.total_reservations >= 5:
            self.vip_level = "frecuente"
        else:
            self.vip_level = "normal"

    def __repr__(self):
        return f"<Client {self.full_name} ({self.vip_level}, {self.total_reservations} reservas)>"
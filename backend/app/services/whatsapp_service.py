"""
Servicio de WhatsApp con Twilio.

Este servicio envía notificaciones automáticas al cliente y al personal.
"""

from twilio.rest import Client
from typing import Optional
from app.core.config import settings
from app.models import Reservation


class WhatsAppService:
    """Servicio para enviar mensajes de WhatsApp via Twilio"""
    
    def __init__(self):
        """Inicializa el cliente de Twilio si las credenciales están configuradas"""
        if settings.TWILIO_ACCOUNT_SID and settings.TWILIO_AUTH_TOKEN:
            self.client = Client(
                settings.TWILIO_ACCOUNT_SID, 
                settings.TWILIO_AUTH_TOKEN
            )
            self.from_whatsapp = settings.TWILIO_WHATSAPP_FROM
            self.admin_whatsapp = settings.ADMIN_WHATSAPP
            self.enabled = True
        else:
            self.client = None
            self.enabled = False
    
    def send_confirmation(self, reservation: Reservation) -> bool:
        """
        Envía confirmación de reserva al cliente.
        
        Args:
            reservation: Objeto de reserva
            
        Returns:
            True si se envió exitosamente, False si hubo error o está deshabilitado
        """
        if not self.enabled:
            print("⚠️  WhatsApp deshabilitado - configura Twilio en .env")
            return False
        
        try:
            # Formatear el mensaje
            message = self._format_confirmation_message(reservation)
            
            # Preparar número del cliente (debe estar en formato internacional)
            to_whatsapp = f"whatsapp:{reservation.client.phone}"
            
            # Enviar mensaje
            self.client.messages.create(
                body=message,
                from_=self.from_whatsapp,
                to=to_whatsapp
            )
            
            print(f"✅ Confirmación enviada a {reservation.client.full_name}")
            return True
            
        except Exception as e:
            print(f"❌ Error enviando WhatsApp: {str(e)}")
            return False
    
    def send_pending_notification(self, reservation: Reservation) -> bool:
        """
        Envía notificación al cliente sobre reserva pendiente.
        """
        if not self.enabled:
            return False
        
        try:
            message = self._format_pending_message(reservation)
            to_whatsapp = f"whatsapp:{reservation.client.phone}"
            
            self.client.messages.create(
                body=message,
                from_=self.from_whatsapp,
                to=to_whatsapp
            )
            
            print(f"✅ Notificación pendiente enviada a {reservation.client.full_name}")
            return True
            
        except Exception as e:
            print(f"❌ Error enviando WhatsApp: {str(e)}")
            return False
    
    def notify_admin(self, reservation: Reservation, reason: str) -> bool:
        """
        Notifica al personal/admin sobre una reserva que requiere atención.
        
        Args:
            reservation: Objeto de reserva
            reason: Razón de la notificación
        """
        if not self.enabled or not self.admin_whatsapp:
            print("⚠️  Notificaciones admin deshabilitadas")
            return False
        
        try:
            message = self._format_admin_notification(reservation, reason)
            
            self.client.messages.create(
                body=message,
                from_=self.from_whatsapp,
                to=self.admin_whatsapp
            )
            
            print(f"✅ Notificación enviada al admin")
            return True
            
        except Exception as e:
            print(f"❌ Error enviando notificación admin: {str(e)}")
            return False
    
    def _format_confirmation_message(self, reservation: Reservation) -> str:
        """Formatea el mensaje de confirmación para el cliente"""
        date_str = reservation.date.strftime("%d/%m/%Y")
        
        msg = f"""🎉 *Reserva Confirmada - Jamonería*

Hola {reservation.client.full_name}!

Tu reserva ha sido confirmada:

📅 Fecha: {date_str}
🕐 Hora: {reservation.time}
👥 Personas: {reservation.pax}
"""
        
        if reservation.table and reservation.table.type == "cava":
            msg += "🍷 Mesa: Cava (especial)\n"
        elif reservation.table:
            msg += f"🪑 Mesa: {reservation.table.name}\n"
        
        if reservation.event_type != "normal":
            msg += f"🎊 Ocasión: {reservation.event_type.capitalize()}\n"
        
        msg += "\n¡Te esperamos! 🍴"
        
        return msg
    
    def _format_pending_message(self, reservation: Reservation) -> str:
        """Formatea el mensaje de reserva pendiente"""
        date_str = reservation.date.strftime("%d/%m/%Y")
        
        msg = f"""⏳ *Reserva Recibida - Jamonería*

Hola {reservation.client.full_name}!

Hemos recibido tu solicitud de reserva:

📅 Fecha: {date_str}
🕐 Hora: {reservation.time}
👥 Personas: {reservation.pax}

Tu reserva está *pendiente de confirmación*. 
Te contactaremos pronto para confirmar.

Gracias por tu paciencia! 🙏
"""
        return msg
    
    def _format_admin_notification(self, reservation: Reservation, reason: str) -> str:
        """Formatea la notificación para el admin/personal"""
        date_str = reservation.date.strftime("%d/%m/%Y")
        
        msg = f"""🔔 *Nueva Reserva Requiere Atención*

📋 ID: #{reservation.id}
👤 Cliente: {reservation.client.full_name}
📞 Tel: {reservation.client.phone}
⭐ Nivel: {reservation.client.vip_level.upper()}

📅 Fecha: {date_str}
🕐 Hora: {reservation.time}
👥 PAX: {reservation.pax}
"""
        
        if reservation.event_type != "normal":
            msg += f"🎊 Evento: {reservation.event_type}\n"
        
        if reservation.requested_cava:
            msg += "🍷 Solicita: CAVA\n"
        
        msg += f"\n⚠️ Razón: {reason}\n"
        msg += "\n👉 Revisar en panel admin"
        
        return msg


# Instancia global del servicio
whatsapp_service = WhatsAppService()
"""
Servicio de WhatsApp con Twilio.
"""

from twilio.rest import Client
from typing import Optional
from app.core.config import settings
from app.models import Reservation


class WhatsAppService:

    def __init__(self):
        if settings.TWILIO_ACCOUNT_SID and settings.TWILIO_AUTH_TOKEN:
            self.client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
            self.from_whatsapp = settings.TWILIO_WHATSAPP_FROM
            self.admin_whatsapp = settings.ADMIN_WHATSAPP
            self.enabled = True
        else:
            self.client = None
            self.enabled = False

    # ── Notificaciones al cliente ─────────────────────────────────────────────

    def send_confirmation(self, reservation: Reservation) -> bool:
        if not self.enabled:
            print("⚠️  WhatsApp deshabilitado - configura Twilio en .env")
            return False
        try:
            self.client.messages.create(
                body=self._format_confirmation_message(reservation),
                from_=self.from_whatsapp,
                to=f"whatsapp:{reservation.client.phone}"
            )
            print(f"✅ Confirmación enviada a {reservation.client.full_name}")
            return True
        except Exception as e:
            print(f"❌ Error enviando WhatsApp: {e}")
            return False

    def send_pending_notification(self, reservation: Reservation) -> bool:
        if not self.enabled:
            return False
        try:
            self.client.messages.create(
                body=self._format_pending_message(reservation),
                from_=self.from_whatsapp,
                to=f"whatsapp:{reservation.client.phone}"
            )
            print(f"✅ Notificación pendiente enviada a {reservation.client.full_name}")
            return True
        except Exception as e:
            print(f"❌ Error enviando WhatsApp: {e}")
            return False

    # ── Notificaciones al admin / encargados ──────────────────────────────────

    def notify_admin(self, reservation: Reservation, reason: str) -> bool:
        """Aviso genérico al admin para reservas pendientes."""
        if not self.enabled or not self.admin_whatsapp:
            print("⚠️  Notificaciones admin deshabilitadas")
            return False
        try:
            self.client.messages.create(
                body=self._format_admin_notification(reservation, reason),
                from_=self.from_whatsapp,
                to=self.admin_whatsapp
            )
            print("✅ Notificación enviada al admin")
            return True
        except Exception as e:
            print(f"❌ Error enviando notificación admin: {e}")
            return False

    def notify_large_group(self, reservation: Reservation) -> bool:
        """
        Avisa al encargado que hay un grupo de 5-15 personas.
        Acción esperada: armar mesa especial y avisar a cocina.
        """
        if not self.enabled or not self.admin_whatsapp:
            print("⚠️  Notificaciones admin deshabilitadas")
            return False
        try:
            self.client.messages.create(
                body=self._format_large_group_message(reservation),
                from_=self.from_whatsapp,
                to=self.admin_whatsapp
            )
            print(f"✅ Aviso grupo grande enviado ({reservation.pax} personas)")
            return True
        except Exception as e:
            print(f"❌ Error enviando aviso grupo grande: {e}")
            return False

    def notify_manager_required(self, reservation: Reservation) -> bool:
        """
        Avisa al encargado que hay un grupo de más de 15 personas
        y que debe gestionar la reserva manualmente.
        """
        if not self.enabled or not self.admin_whatsapp:
            print("⚠️  Notificaciones admin deshabilitadas")
            return False
        try:
            self.client.messages.create(
                body=self._format_manager_required_message(reservation),
                from_=self.from_whatsapp,
                to=self.admin_whatsapp
            )
            print(f"✅ Aviso encargado enviado ({reservation.pax} personas)")
            return True
        except Exception as e:
            print(f"❌ Error enviando aviso encargado: {e}")
            return False

    # ── Formatters ────────────────────────────────────────────────────────────

    def _format_confirmation_message(self, reservation: Reservation) -> str:
        date_str = reservation.date.strftime("%d/%m/%Y")
        msg = (
            f"🎉 *Reserva Confirmada - MM*\n\n"
            f"Hola {reservation.client.full_name}!\n\n"
            f"Tu reserva ha sido confirmada:\n\n"
            f"📅 Fecha: {date_str}\n"
            f"🕐 Hora: {reservation.time}\n"
            f"👥 Personas: {reservation.pax}\n"
        )
        if reservation.table and reservation.table.type == "cava":
            msg += "Mesa: Cava (especial)\n"
        elif reservation.table:
            msg += f"Mesa: {reservation.table.name}\n"
        if reservation.event_type != "normal":
            msg += f"Ocasión: {reservation.event_type.capitalize()}\n"
        msg += "\nMuchas gracias por elegirnos. Los esperamos en calle Noruega 1382, oeste capital."
        return msg

    def _format_pending_message(self, reservation: Reservation) -> str:
        date_str = reservation.date.strftime("%d/%m/%Y")
        return (
            f"⏳ *Reserva Recibida - Jamonería*\n\n"
            f"Hola {reservation.client.full_name}!\n\n"
            f"Recibimos tu solicitud:\n\n"
            f"📅 Fecha: {date_str}\n"
            f"🕐 Hora: {reservation.time}\n"
            f"👥 Personas: {reservation.pax}\n\n"
            f"Tu reserva está *pendiente de confirmación*.\n"
            f"Te contactaremos pronto. Gracias! 🙏"
        )

    def _format_admin_notification(self, reservation: Reservation, reason: str) -> str:
        date_str = reservation.date.strftime("%d/%m/%Y")
        msg = (
            f"🔔 *Nueva Reserva Requiere Atención*\n\n"
            f"📋 ID: #{reservation.id}\n"
            f"👤 {reservation.client.full_name}\n"
            f"📞 {reservation.client.phone}\n"
            f"⭐ {reservation.client.vip_level.upper()}\n\n"
            f"📅 {date_str} — 🕐 {reservation.time} — 👥 {reservation.pax} pax\n"
        )
        if reservation.event_type != "normal":
            msg += f"🎊 Evento: {reservation.event_type}\n"
        if reservation.requested_cava:
            msg += "🍷 Solicita: CAVA\n"
        msg += f"\n⚠️ {reason}\n\n👉 Revisar en panel admin"
        return msg

    def _format_large_group_message(self, reservation: Reservation) -> str:
        """Mensaje para grupos de 5 a 15 personas: armar mesa especial + avisar a cocina."""
        date_str = reservation.date.strftime("%d/%m/%Y")
        return (
            f"🪑 *Grupo Grande — Armar Mesa Especial*\n\n"
            f"Llegó una reserva de *{reservation.pax} personas* "
            f"que necesita preparación especial.\n\n"
            f"📋 ID: #{reservation.id}\n"
            f"👤 {reservation.client.full_name}\n"
            f"📞 {reservation.client.phone}\n\n"
            f"📅 {date_str} — 🕐 {reservation.time}\n"
            f"🎉 Ocasión: {reservation.event_type.capitalize()}\n\n"
            f"✅ *Acciones requeridas:*\n"
            f"  1. Armar mesa especial para {reservation.pax} personas\n"
            f"  2. Avisar a cocina para que los espere\n"
            f"  3. Confirmar reserva en el panel admin\n\n"
            f"👉 Panel admin para confirmar"
        )

    def _format_manager_required_message(self, reservation: Reservation) -> str:
        """Mensaje para grupos de más de 15 personas: delegado al encargado."""
        date_str = reservation.date.strftime("%d/%m/%Y")
        return (
            f"🚨 *Grupo Muy Grande — Gestión de Encargado*\n\n"
            f"Reserva de *{reservation.pax} personas* recibida.\n"
            f"Supera los 15 cubiertos — requiere gestión manual completa.\n\n"
            f"📋 ID: #{reservation.id}\n"
            f"👤 {reservation.client.full_name}\n"
            f"📞 {reservation.client.phone}\n"
            f"⭐ {reservation.client.vip_level.upper()}\n\n"
            f"📅 {date_str} — 🕐 {reservation.time}\n"
            f"🎉 Ocasión: {reservation.event_type.capitalize()}\n\n"
            f"✅ *Encargado debe:*\n"
            f"  1. Contactar al cliente para coordinar\n"
            f"  2. Definir disposición de mesas\n"
            f"  3. Coordinar menú y tiempos con cocina\n"
            f"  4. Confirmar o rechazar en el panel admin\n\n"
            f"⚠️ El sistema NO asignó mesa automáticamente."
        )


# Instancia global
whatsapp_service = WhatsAppService()
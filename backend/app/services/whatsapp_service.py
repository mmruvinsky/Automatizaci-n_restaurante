"""
Servicio de WhatsApp con Twilio.

Destinatarios configurables en .env:
  ADMIN_WHATSAPP   → encargado (todas las alertas operativas)
  CHEF_WHATSAPP    → chef (grupos grandes, resúmenes)
  OWNER_WHATSAPP   → dueño (solo resúmenes)
"""

from twilio.rest import Client
from typing import Optional, List
from app.core.config import settings
from app.models import Reservation


class WhatsAppService:

    def __init__(self):
        if settings.TWILIO_ACCOUNT_SID and settings.TWILIO_AUTH_TOKEN:
            self.client      = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
            self.from_number = settings.TWILIO_WHATSAPP_FROM
            self.admin       = settings.ADMIN_WHATSAPP
            self.chef        = settings.CHEF_WHATSAPP
            self.owner       = settings.OWNER_WHATSAPP
            self.enabled     = True
        else:
            self.client      = None
            self.enabled     = False

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _send(self, to: Optional[str], body: str, label: str) -> bool:
        """Envío genérico con manejo de errores centralizado."""
        if not self.enabled:
            print(f"⚠️  WhatsApp deshabilitado — mensaje para {label} no enviado")
            return False
        if not to:
            print(f"⚠️  Sin número configurado para {label}")
            return False
        try:
            self.client.messages.create(body=body, from_=self.from_number, to=to)
            print(f"✅ WhatsApp → {label}")
            return True
        except Exception as e:
            print(f"❌ Error enviando a {label}: {e}")
            return False

    # ── Cliente ───────────────────────────────────────────────────────────────

    def send_confirmation(self, reservation: Reservation) -> bool:
        """Confirmación al cliente cuando su reserva es aprobada."""
        return self._send(
            f"whatsapp:{reservation.client.phone}",
            self._fmt_confirmation(reservation),
            f"cliente {reservation.client.full_name}"
        )

    def send_pending_notification(self, reservation: Reservation) -> bool:
        """Aviso al cliente de que su reserva está pendiente de confirmación."""
        return self._send(
            f"whatsapp:{reservation.client.phone}",
            self._fmt_pending(reservation),
            f"cliente {reservation.client.full_name}"
        )

    # ── Alertas operativas ────────────────────────────────────────────────────

    def notify_large_group(self, reservation: Reservation) -> None:
        """
        Grupo de 5-15 personas.
        → Encargado: armar mesa especial y confirmar en panel
        → Chef: prepararse para grupo grande
        """
        self._send(self.admin, self._fmt_large_group_manager(reservation), "encargado (grupo grande)")
        self._send(self.chef,  self._fmt_large_group_chef(reservation),    "chef (grupo grande)")

    def notify_manager_required(self, reservation: Reservation) -> None:
        """
        Grupo > 15 personas.
        → Encargado: gestión manual completa
        → Chef: coordinar menú y tiempos
        """
        self._send(self.admin, self._fmt_manager_required_manager(reservation), "encargado (grupo >15)")
        self._send(self.chef,  self._fmt_manager_required_chef(reservation),    "chef (grupo >15)")

    def notify_admin(self, reservation: Reservation, reason: str) -> bool:
        """Aviso genérico al encargado (cava no disponible, casos especiales)."""
        return self._send(
            self.admin,
            self._fmt_admin(reservation, reason),
            "encargado (aviso genérico)"
        )

    # ── Resúmenes ─────────────────────────────────────────────────────────────

    def send_summary(self, reservations: List[Reservation], turno: str = "noche") -> None:
        """
        Resumen del turno. Se llama desde el scheduler en main.py.
        turno: "mediodia" o "noche"
        Destinatarios: encargado + chef + dueño
        """
        body  = self._fmt_summary(reservations, turno)
        label = "mediodía" if turno == "mediodia" else "noche"
        self._send(self.admin, body, f"encargado (resumen {label})")
        self._send(self.chef,  body, f"chef (resumen {label})")
        self._send(self.owner, body, f"dueño (resumen {label})")

    # ── Formatters — cliente ──────────────────────────────────────────────────

    def _fmt_confirmation(self, r: Reservation) -> str:
        date_str = r.date.strftime("%d/%m/%Y")
        msg = (
            f"🎉 *Reserva Confirmada — MM*\n\n"
            f"Hola {r.client.full_name}!\n\n"
            f"Tu reserva ha sido confirmada:\n"
            f"📅 {date_str}  🕐 {r.time}  👥 {r.pax} personas\n"
        )
        if r.table and r.table.type == "cava":
            msg += "🍷 Mesa: Cava\n"
        elif r.table:
            msg += f"🪑 Mesa: {r.table.name}\n"
        if r.event_type != "normal":
            msg += f"🎊 Ocasión: {r.event_type.capitalize()}\n"
        msg += "\nLos esperamos en Calle Noruega 1382, Mendoza. ¡Gracias!"
        return msg

    def _fmt_pending(self, r: Reservation) -> str:
        date_str = r.date.strftime("%d/%m/%Y")
        return (
            f"⏳ *Reserva Recibida — MM*\n\n"
            f"Hola {r.client.full_name}!\n\n"
            f"Recibimos tu solicitud:\n"
            f"📅 {date_str}  🕐 {r.time}  👥 {r.pax} personas\n\n"
            f"Tu reserva está *pendiente de confirmación*.\n"
            f"Te contactaremos pronto. ¡Gracias! 🙏"
        )

    # ── Formatters — alertas operativas ──────────────────────────────────────

    def _fmt_admin(self, r: Reservation, reason: str) -> str:
        date_str = r.date.strftime("%d/%m/%Y")
        msg = (
            f"🔔 *Nueva reserva requiere atención*\n\n"
            f"#{r.id} · {r.client.full_name} · ⭐ {r.client.vip_level.upper()}\n"
            f"📞 {r.client.phone}\n"
            f"📅 {date_str}  🕐 {r.time}  👥 {r.pax} pax\n"
        )
        if r.requested_cava:
            msg += "🍷 Solicita cava\n"
        msg += f"\n⚠️ {reason}\n👉 Revisar en panel admin"
        return msg

    def _fmt_large_group_manager(self, r: Reservation) -> str:
        date_str = r.date.strftime("%d/%m/%Y")
        return (
            f"🪑 *Grupo grande — Armar mesa especial*\n\n"
            f"#{r.id} · {r.client.full_name}\n"
            f"📞 {r.client.phone}\n"
            f"📅 {date_str}  🕐 {r.time}  👥 *{r.pax} personas*\n"
            f"🎉 Ocasión: {r.event_type.capitalize()}\n\n"
            f"✅ *Acciones requeridas:*\n"
            f"  1. Armar mesa especial para {r.pax} personas\n"
            f"  2. Avisar a cocina\n"
            f"  3. Confirmar reserva en el panel admin"
        )

    def _fmt_large_group_chef(self, r: Reservation) -> str:
        date_str = r.date.strftime("%d/%m/%Y")
        return (
            f"👨‍🍳 *Aviso cocina — Grupo grande*\n\n"
            f"Llega una reserva de *{r.pax} personas*.\n\n"
            f"📅 {date_str}  🕐 {r.time}\n"
            f"🎉 Ocasión: {r.event_type.capitalize()}\n"
            f"👤 {r.client.full_name}\n\n"
            f"Tenerlo en cuenta para mise en place y tiempos de servicio."
        )

    def _fmt_manager_required_manager(self, r: Reservation) -> str:
        date_str = r.date.strftime("%d/%m/%Y")
        return (
            f"🚨 *Grupo muy grande — Gestión manual*\n\n"
            f"#{r.id} · {r.client.full_name} · ⭐ {r.client.vip_level.upper()}\n"
            f"📞 {r.client.phone}\n"
            f"📅 {date_str}  🕐 {r.time}  👥 *{r.pax} personas*\n"
            f"🎉 Ocasión: {r.event_type.capitalize()}\n\n"
            f"✅ *Encargado debe:*\n"
            f"  1. Contactar al cliente para coordinar\n"
            f"  2. Definir disposición de mesas\n"
            f"  3. Coordinar con cocina\n"
            f"  4. Confirmar o rechazar en el panel\n\n"
            f"⚠️ El sistema NO asignó mesa automáticamente."
        )

    def _fmt_manager_required_chef(self, r: Reservation) -> str:
        date_str = r.date.strftime("%d/%m/%Y")
        return (
            f"👨‍🍳 *Aviso cocina — Evento grande*\n\n"
            f"Reserva de *{r.pax} personas* pendiente de confirmación.\n\n"
            f"📅 {date_str}  🕐 {r.time}\n"
            f"🎉 Ocasión: {r.event_type.capitalize()}\n"
            f"👤 {r.client.full_name}\n\n"
            f"Coordinar con el encargado para menú, tiempos y disposición.\n"
            f"⚠️ Aún no está confirmada."
        )

    # ── Formatter — resumen de turno ──────────────────────────────────────────

    def _fmt_summary(self, reservations: List[Reservation], turno: str) -> str:
        from datetime import datetime
        tz       = settings.get_timezone()
        now      = datetime.now(tz)
        date_str = now.strftime("%d/%m/%Y")

        if turno == "mediodia":
            emoji  = "☀️"
            titulo = "Resumen de mediodía"
        else:
            emoji  = "🌙"
            titulo = "Resumen de noche"

        # Solo reservas no canceladas
        activas    = [r for r in reservations if r.status != "cancelled"]
        confirmed  = [r for r in activas if r.status == "confirmed"]
        pending    = [r for r in activas if r.status == "pending"]
        total_pax  = sum(r.pax for r in activas)
        vip_count  = sum(1 for r in activas if r.client and r.client.vip_level == "vip")
        cava_count = sum(1 for r in activas if r.requested_cava)
        special    = [r for r in activas if r.special_flag]

        msg = (
            f"{emoji} *{titulo} — {date_str}*\n"
            f"━━━━━━━━━━━━━━━━━━━━\n\n"
            f"📊 *Resumen general*\n"
            f"  • Reservas activas:   {len(activas)}\n"
            f"  • Confirmadas:        {len(confirmed)}\n"
            f"  • Pendientes:         {len(pending)}\n"
            f"  • Total cubiertos:    {total_pax}\n"
            f"  • Clientes VIP:       {vip_count}\n"
            f"  • Solicitan cava:     {cava_count}\n"
        )

        if special:
            msg += f"  • Grupos especiales:  {len(special)}\n"

        if confirmed:
            msg += f"\n✅ *Confirmadas ({len(confirmed)})*\n"
            for r in sorted(confirmed, key=lambda x: x.time):
                mesa = r.table.name if r.table else "sin mesa"
                vip  = " ⭐" if r.client and r.client.vip_level == "vip" else ""
                msg += f"  {r.time} · {r.client.full_name}{vip} · {r.pax} pax · {mesa}\n"

        if pending:
            msg += f"\n⏳ *Pendientes — requieren atención ({len(pending)})*\n"
            for r in sorted(pending, key=lambda x: x.time):
                msg += f"  {r.time} · {r.client.full_name} · {r.pax} pax\n"
                msg += f"         📞 {r.client.phone}\n"

        if not activas:
            msg += f"\n😴 Sin reservas para este turno.\n"

        msg += "\n━━━━━━━━━━━━━━━━━━━━\n👉 Panel admin para gestionar pendientes."
        return msg


# Instancia global
whatsapp_service = WhatsAppService()
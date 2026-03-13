"""
Servicio de Reservas - Lógica de negocio.

Reglas de grupo (sin límite de pax):
  ≤ 4  → confirmación automática, mesa estándar
  5-15 → mesa especial + aviso a cocina (special_flag=True)
  > 15 → delegado a encargado humano, sin asignación automática
"""

from sqlalchemy.orm import Session
from datetime import datetime, date, time, timedelta
from typing import Optional, List, Tuple
import pytz

from app.models import Table, Client, Reservation
from app.schemas import ReservationCreate
from app.core.config import settings

# ── Umbrales de grupo ─────────────────────────────────────────────────────────
LARGE_GROUP_THRESHOLD = 4   # > 4: mesa especial + aviso cocina
MANAGER_THRESHOLD = 15      # > 15: delegar a encargado humano


# ── Excepciones de dominio ────────────────────────────────────────────────────

class ReservationNotFoundError(Exception):
    """La reserva solicitada no existe."""

class TableUnavailableError(Exception):
    """La mesa solicitada no está disponible en ese horario."""

class InvalidReservationDataError(Exception):
    """Los datos de la reserva son inválidos."""


# ── Servicio ──────────────────────────────────────────────────────────────────

class ReservationService:

    def __init__(self, db: Session):
        self.db = db
        self.tz = settings.get_timezone()

    def create_reservation(self, reservation_data: ReservationCreate) -> Tuple[Reservation, str]:
        client = self._get_or_create_client(
            name=reservation_data.customer_name,
            phone=reservation_data.customer_phone,
            email=reservation_data.customer_email
        )

        reservation = Reservation(
            client_id=client.id,
            date=self._parse_date_time(reservation_data.date, reservation_data.time),
            time=reservation_data.time,
            pax=reservation_data.pax,
            event_type=reservation_data.event_type,
            requested_cava=reservation_data.requested_cava,
            notes=reservation_data.notes,
            status="pending"
        )

        self._apply_business_rules(reservation, client)
        assigned, message = self._assign_table(reservation, client)

        self.db.add(reservation)
        client.total_reservations += 1
        client.last_visit_at = datetime.now(self.tz)
        client.update_vip_level()

        self.db.commit()
        self.db.refresh(reservation)
        return reservation, message

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _get_or_create_client(self, name: str, phone: str, email: Optional[str]) -> Client:
        client = self.db.query(Client).filter(Client.phone == phone).first()
        if not client:
            client = Client(full_name=name, phone=phone, email=email)
            self.db.add(client)
            self.db.flush()
        return client

    def _parse_date_time(self, date_obj: date, time_str: str) -> datetime:
        hour, minute = map(int, time_str.split(':'))
        dt = datetime.combine(date_obj, time(hour, minute))
        return self.tz.localize(dt)

    # ── Reglas de negocio ─────────────────────────────────────────────────────

    def _apply_business_rules(self, reservation: Reservation, client: Client):
        pax = reservation.pax

        if pax > MANAGER_THRESHOLD:
            # Requiere gestión humana — encargado se hace cargo
            reservation.status = "pending"
            reservation.special_flag = True
            reservation.admin_notes = (
                f"GRUPO GRANDE ({pax} personas) — delegado a encargado. "
                "Requiere coordinación manual de mesas y aviso a cocina."
            )

        elif pax > LARGE_GROUP_THRESHOLD:
            # Mesa especial + cocina debe estar lista
            reservation.status = "pending"
            reservation.special_flag = True
            reservation.admin_notes = (
                f"Grupo de {pax} personas — armar mesa especial y avisar a cocina."
            )

        else:
            # ≤ 4: flujo normal
            reservation.status = "pending"
            reservation.special_flag = False

    def _assign_table(self, reservation: Reservation, client: Client) -> Tuple[bool, str]:
        pax = reservation.pax
        is_vip = client.vip_level == "vip"

        # Grupos > 15: sin asignación automática, encargado gestiona
        if pax > MANAGER_THRESHOLD:
            return False, (
                f"Grupo de {pax} personas — encargado notificado para gestión manual."
            )

        # Cava: VIP o evento especial + solicitada + ≤ 6
        if (is_vip or reservation.is_event_special) and reservation.requested_cava and pax <= 6:
            if self._is_cava_available(reservation.date, reservation.time):
                cava_table = self.db.query(Table).filter(
                    Table.type == "cava",
                    Table.is_active == True
                ).first()
                if cava_table:
                    reservation.table_id = cava_table.id
                    reservation.status = "confirmed"
                    label = "Cliente VIP" if is_vip else "Evento especial"
                    return True, f"Cava asignada automáticamente ({label})"

            reservation.status = "pending"
            reservation.admin_notes = "Cliente solicita cava - verificar disponibilidad"
            return False, "Cava no disponible - reserva pendiente de confirmación"

        # ≤ 4: mesa estándar automática
        if pax <= LARGE_GROUP_THRESHOLD:
            standard_table = self._find_available_standard_table(
                reservation.date, reservation.time, pax
            )
            if standard_table:
                reservation.table_id = standard_table.id
                reservation.status = "confirmed"
                return True, "Mesa asignada automáticamente"
            reservation.status = "pending"
            return False, "No hay mesas disponibles - reserva pendiente"

        # 5-15: pendiente, encargado arma mesa especial
        return False, (
            f"Grupo de {pax} personas — pendiente armado de mesa especial y aviso a cocina."
        )

    # ── Disponibilidad ────────────────────────────────────────────────────────

    def _is_cava_available(self, date: datetime, time: str) -> bool:
        cava_table = self.db.query(Table).filter(
            Table.type == "cava", Table.is_active == True
        ).first()
        if not cava_table:
            return False
        time_start = date - timedelta(hours=3)
        time_end = date + timedelta(hours=3)
        conflict = self.db.query(Reservation).filter(
            Reservation.table_id == cava_table.id,
            Reservation.date >= time_start,
            Reservation.date <= time_end,
            Reservation.status.in_(["confirmed", "pending"])
        ).first()
        return conflict is None

    def _find_available_standard_table(
        self, date: datetime, time: str, pax: int
    ) -> Optional[Table]:
        suitable_tables = self.db.query(Table).filter(
            Table.type == "standard",
            Table.capacity >= pax,
            Table.is_active == True
        ).order_by(Table.capacity).all()

        if not suitable_tables:
            return None

        time_start = date - timedelta(hours=3)
        time_end = date + timedelta(hours=3)

        for table in suitable_tables:
            conflict = self.db.query(Reservation).filter(
                Reservation.table_id == table.id,
                Reservation.date >= time_start,
                Reservation.date <= time_end,
                Reservation.status.in_(["confirmed", "pending"])
            ).first()
            if not conflict:
                return table
        return None

    def get_reservations_by_date(self, target_date: date) -> List[Reservation]:
        start = datetime.combine(target_date, time.min)
        end = datetime.combine(target_date, time.max)
        return self.db.query(Reservation).filter(
            Reservation.date >= self.tz.localize(start),
            Reservation.date <= self.tz.localize(end)
        ).all()

    def update_reservation_status(
        self,
        reservation_id: int,
        status: str,
        table_id: Optional[int] = None,
        admin_notes: Optional[str] = None
    ) -> Reservation:
        reservation = self.db.query(Reservation).filter(
            Reservation.id == reservation_id
        ).first()

        if not reservation:
            raise ReservationNotFoundError(f"Reserva #{reservation_id} no encontrada")

        if table_id is not None:
            time_start = reservation.date - timedelta(hours=3)
            time_end = reservation.date + timedelta(hours=3)
            conflict = self.db.query(Reservation).filter(
                Reservation.table_id == table_id,
                Reservation.date >= time_start,
                Reservation.date <= time_end,
                Reservation.status.in_(["confirmed", "pending"]),
                Reservation.id != reservation_id
            ).first()
            if conflict:
                raise TableUnavailableError(
                    f"La mesa {table_id} ya tiene una reserva en ese horario (reserva #{conflict.id})"
                )
            reservation.table_id = table_id

        reservation.status = status
        if admin_notes is not None:
            reservation.admin_notes = admin_notes

        self.db.commit()
        self.db.refresh(reservation)
        return reservation
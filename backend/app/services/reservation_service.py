"""
Servicio de Reservas - Contiene toda la lógica de negocio.
"""

from sqlalchemy.orm import Session
from datetime import datetime, date, time, timedelta
from typing import Optional, List, Tuple
import pytz

from app.models import Table, Client, Reservation
from app.schemas import ReservationCreate
from app.core.config import settings


# ── Excepciones de dominio ────────────────────────────────────────────────────

class ReservationNotFoundError(Exception):
    """La reserva solicitada no existe."""


class TableUnavailableError(Exception):
    """La mesa solicitada no está disponible en ese horario."""


class InvalidReservationDataError(Exception):
    """Los datos de la reserva son inválidos."""


# ── Servicio ──────────────────────────────────────────────────────────────────

class ReservationService:
    """Servicio que maneja toda la lógica de reservas"""

    def __init__(self, db: Session):
        self.db = db
        self.tz = settings.get_timezone()

    def create_reservation(self, reservation_data: ReservationCreate) -> Tuple[Reservation, str]:
        """
        Crea una nueva reserva aplicando todas las reglas de negocio.

        Returns:
            (reserva, mensaje): Tupla con la reserva creada y un mensaje informativo
        """
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

    def _apply_business_rules(self, reservation: Reservation, client: Client):
        pax = reservation.pax

        if pax <= 4:
            reservation.status = "pending"
            reservation.special_flag = False
        elif pax <= 6:
            reservation.special_flag = True
            reservation.status = "pending"
        else:
            reservation.status = "pending"
            reservation.special_flag = True
            reservation.admin_notes = "Reserva de grupo grande - requiere confirmación manual"

    def _assign_table(self, reservation: Reservation, client: Client) -> Tuple[bool, str]:
        pax = reservation.pax
        is_vip = client.vip_level == "vip"

        # Caso 1: VIP o evento especial + cava solicitada
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

        # Caso 2: ≤4 pax → mesa estándar automática
        if pax <= 4:
            standard_table = self._find_available_standard_table(
                reservation.date, reservation.time, pax
            )
            if standard_table:
                reservation.table_id = standard_table.id
                reservation.status = "confirmed"
                return True, "Mesa asignada automáticamente"
            reservation.status = "pending"
            return False, "No hay mesas disponibles - reserva pendiente"

        # Caso 3: 5-6 pax
        if pax <= 6:
            reservation.status = "pending"
            reservation.admin_notes = "Verificar disponibilidad para 5-6 personas"
            return False, "Reserva pendiente de confirmación (5-6 personas)"

        # Caso 4: >6 pax
        reservation.status = "pending"
        reservation.admin_notes = f"Grupo grande ({pax} personas) - requiere configuración de mesas"
        return False, "Reserva pendiente - grupo grande requiere confirmación"

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
        """
        Actualiza el estado de una reserva.

        Raises:
            ReservationNotFoundError: si la reserva no existe.
            TableUnavailableError: si la mesa ya está ocupada en ese horario.
        """
        reservation = self.db.query(Reservation).filter(
            Reservation.id == reservation_id
        ).first()

        if not reservation:
            raise ReservationNotFoundError(f"Reserva #{reservation_id} no encontrada")

        if table_id is not None:
            # Verificar que la mesa no tenga otro conflicto (excluyendo esta misma reserva)
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
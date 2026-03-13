"""
Tests de reglas de negocio — ReservationService.

Cubre:
- Asignación automática de mesas por capacidad (pax)
- Lógica de la cava (VIP, eventos especiales, disponibilidad)
- Flags especiales y estados resultantes
- Comportamiento sin mesas disponibles

Ejecutar:
    cd backend
    pytest tests/test_reservation_business_rules.py -v
"""

import pytest
from datetime import date, timedelta
from unittest.mock import MagicMock, patch
from sqlalchemy.orm import Session

from app.models import Client, Table, Reservation
from app.schemas.reservation import ReservationCreate
from app.services.reservation_service import (
    ReservationService,
    ReservationNotFoundError,
    TableUnavailableError,
)


# ── Helpers ───────────────────────────────────────────────────────────────────

def make_client(vip_level: str = "normal", total_reservations: int = 2) -> Client:
    """Crea un cliente mock con el nivel VIP indicado."""
    client = MagicMock(spec=Client)
    client.id = 1
    client.full_name = "Test Cliente"
    client.phone = "+5492614000000"
    client.email = None
    client.vip_level = vip_level
    client.total_reservations = total_reservations
    return client


def make_table(
    table_id: int = 1,
    name: str = "Mesa 1",
    capacity: int = 4,
    table_type: str = "standard",
    is_active: bool = True,
) -> Table:
    """Crea una mesa mock."""
    table = MagicMock(spec=Table)
    table.id = table_id
    table.name = name
    table.capacity = capacity
    table.type = table_type
    table.is_active = is_active
    return table


def make_reservation_data(
    pax: int = 2,
    event_type: str = "normal",
    requested_cava: bool = False,
    time: str = "20:30",
) -> ReservationCreate:
    """Crea datos de reserva para el formulario público."""
    tomorrow = date.today() + timedelta(days=1)
    return ReservationCreate(
        customer_name="Test Cliente",
        customer_phone="+5492614000000",
        customer_email=None,
        date=tomorrow,
        time=time,
        pax=pax,
        event_type=event_type,
        requested_cava=requested_cava,
        notes=None,
    )


def make_service_with_mocks(
    client: Client,
    tables: list,
    existing_reservations: list = None,
) -> ReservationService:
    """
    Construye un ReservationService con una sesión DB completamente mockeada.
    Evita tocar PostgreSQL en los tests.
    """
    db = MagicMock(spec=Session)
    existing_reservations = existing_reservations or []

    def query_side_effect(model):
        mock_query = MagicMock()

        if model == Client:
            mock_query.filter.return_value.first.return_value = client

        elif model == Table:
            def filter_tables(*args, **kwargs):
                inner = MagicMock()
                # Para búsqueda de cava
                cava_tables = [t for t in tables if t.type == "cava" and t.is_active]
                standard_tables = sorted(
                    [t for t in tables if t.type == "standard" and t.is_active],
                    key=lambda t: t.capacity,
                )
                inner.first.return_value = cava_tables[0] if cava_tables else None
                inner.order_by.return_value.all.return_value = standard_tables
                inner.all.return_value = standard_tables
                return inner
            mock_query.filter.side_effect = filter_tables

        elif model == Reservation:
            # Simula que no hay conflictos de horario (mesa libre)
            inner = MagicMock()
            inner.first.return_value = None  # sin conflictos
            mock_query.filter.return_value = inner

        return mock_query

    db.query.side_effect = query_side_effect
    db.add = MagicMock()
    db.flush = MagicMock()
    db.commit = MagicMock()
    db.refresh = MagicMock()

    service = ReservationService(db)
    return service, db


# ── Tests: tamaño del grupo ───────────────────────────────────────────────────

class TestGroupSizeRules:

    def test_pax_lte_4_gets_confirmed_with_standard_table(self):
        """≤4 pax con mesa disponible → confirmado automáticamente."""
        client = make_client()
        tables = [make_table(capacity=4)]
        service, db = make_service_with_mocks(client, tables)

        data = make_reservation_data(pax=2)
        reservation = Reservation()
        reservation.pax = data.pax
        reservation.event_type = data.event_type
        reservation.requested_cava = data.requested_cava
        reservation.status = "pending"
        reservation.special_flag = False
        reservation.admin_notes = None

        service._apply_business_rules(reservation, client)
        service._assign_table(reservation, client)

        assert reservation.status == "confirmed"
        assert reservation.special_flag is False
        assert reservation.table_id == tables[0].id

    def test_pax_5_6_sets_special_flag_and_pending(self):
        """5-6 pax → special_flag=True, status=pending."""
        client = make_client()
        tables = [make_table(capacity=6)]
        service, db = make_service_with_mocks(client, tables)

        for pax in [5, 6]:
            reservation = Reservation()
            reservation.pax = pax
            reservation.event_type = "normal"
            reservation.requested_cava = False
            reservation.status = "pending"
            reservation.special_flag = False
            reservation.admin_notes = None

            service._apply_business_rules(reservation, client)

            assert reservation.special_flag is True, f"pax={pax} debería tener special_flag=True"
            assert reservation.status == "pending"

    def test_pax_gt_6_sets_special_flag_and_pending_with_note(self):
        """>6 pax → special_flag=True, status=pending, nota de grupo grande."""
        client = make_client()
        tables = [make_table(capacity=8)]
        service, db = make_service_with_mocks(client, tables)

        reservation = Reservation()
        reservation.pax = 8
        reservation.event_type = "normal"
        reservation.requested_cava = False
        reservation.status = "pending"
        reservation.special_flag = False
        reservation.admin_notes = None

        service._apply_business_rules(reservation, client)

        assert reservation.special_flag is True
        assert reservation.status == "pending"
        assert reservation.admin_notes is not None
        assert "grupo grande" in reservation.admin_notes.lower() or "manual" in reservation.admin_notes.lower()


# ── Tests: lógica de la cava ──────────────────────────────────────────────────

class TestCavaLogic:

    def _make_cava_reservation(self, pax=4, event_type="normal", requested_cava=True):
        reservation = Reservation()
        reservation.pax = pax
        reservation.event_type = event_type
        reservation.requested_cava = requested_cava
        reservation.status = "pending"
        reservation.special_flag = False
        reservation.admin_notes = None
        reservation.table_id = None
        # Simular property is_event_special
        reservation.is_event_special = event_type in ["negocios", "aniversario", "celebracion"]
        return reservation

    def test_vip_client_with_cava_available_gets_cava(self):
        """Cliente VIP + cava disponible + requested_cava → asignado a cava."""
        client = make_client(vip_level="vip")
        cava = make_table(table_id=1, name="Cava", capacity=6, table_type="cava")
        service, db = make_service_with_mocks(client, [cava])

        # Simular cava disponible (sin conflictos)
        db.query.return_value.filter.return_value.first.return_value = None

        reservation = self._make_cava_reservation(pax=4)
        service._assign_table(reservation, client)

        assert reservation.status == "confirmed"
        assert reservation.table_id == cava.id

    def test_special_event_with_cava_available_gets_cava(self):
        """Evento especial + cava disponible + requested_cava → asignado a cava."""
        client = make_client(vip_level="normal")
        cava = make_table(table_id=1, name="Cava", capacity=6, table_type="cava")
        service, db = make_service_with_mocks(client, [cava])

        db.query.return_value.filter.return_value.first.return_value = None

        reservation = self._make_cava_reservation(pax=4, event_type="aniversario")
        service._assign_table(reservation, client)

        assert reservation.status == "confirmed"
        assert reservation.table_id == cava.id

    def test_vip_with_cava_occupied_stays_pending(self):
        """Cliente VIP + cava ocupada → status=pending, nota de verificación."""
        client = make_client(vip_level="vip")
        cava = make_table(table_id=1, name="Cava", capacity=6, table_type="cava")

        # Simular cava ocupada: _is_cava_available devuelve False
        service, db = make_service_with_mocks(client, [cava])
        with patch.object(service, "_is_cava_available", return_value=False):
            reservation = self._make_cava_reservation(pax=4)
            service._assign_table(reservation, client)

        assert reservation.status == "pending"
        assert reservation.admin_notes is not None

    def test_normal_client_requesting_cava_goes_to_standard_table(self):
        """Cliente normal + requested_cava=True pero no es VIP ni evento especial → mesa estándar."""
        client = make_client(vip_level="normal")
        standard = make_table(table_id=2, name="Mesa 2", capacity=4, table_type="standard")
        service, db = make_service_with_mocks(client, [standard])

        reservation = self._make_cava_reservation(pax=2, event_type="normal")
        # Cliente normal sin evento especial no entra al flujo de cava
        service._assign_table(reservation, client)

        assert reservation.status == "confirmed"
        assert reservation.table_id == standard.id

    def test_pax_gt_6_with_vip_and_cava_still_pending(self):
        """VIP + cava + >6 pax → no entra al flujo de cava (límite es ≤6)."""
        client = make_client(vip_level="vip")
        cava = make_table(table_id=1, name="Cava", capacity=8, table_type="cava")
        service, db = make_service_with_mocks(client, [cava])

        reservation = self._make_cava_reservation(pax=8)
        service._assign_table(reservation, client)

        # >6 pax cae en el caso 4: siempre pendiente
        assert reservation.status == "pending"


# ── Tests: sin mesas disponibles ─────────────────────────────────────────────

class TestNoTablesAvailable:

    def test_pax_lte_4_no_tables_available_stays_pending(self):
        """≤4 pax pero sin mesas disponibles → status=pending."""
        client = make_client()
        # Sin mesas en el sistema
        service, db = make_service_with_mocks(client, tables=[])

        reservation = Reservation()
        reservation.pax = 2
        reservation.event_type = "normal"
        reservation.requested_cava = False
        reservation.status = "pending"
        reservation.special_flag = False
        reservation.admin_notes = None
        reservation.is_event_special = False

        assigned, message = service._assign_table(reservation, client)

        assert assigned is False
        assert reservation.status == "pending"


# ── Tests: update_reservation_status ─────────────────────────────────────────

class TestUpdateReservationStatus:

    def test_raises_not_found_for_missing_reservation(self):
        """Actualizar una reserva inexistente lanza ReservationNotFoundError."""
        db = MagicMock(spec=Session)
        db.query.return_value.filter.return_value.first.return_value = None

        service = ReservationService(db)

        with pytest.raises(ReservationNotFoundError):
            service.update_reservation_status(
                reservation_id=9999,
                status="confirmed"
            )

    def test_raises_table_unavailable_on_conflict(self):
        """Asignar mesa con conflicto de horario lanza TableUnavailableError."""
        db = MagicMock(spec=Session)

        # La reserva a actualizar existe
        existing_reservation = MagicMock(spec=Reservation)
        existing_reservation.id = 1
        existing_reservation.date = MagicMock()
        existing_reservation.status = "pending"
        existing_reservation.table = None

        # Hay un conflicto en ese horario
        conflicting_reservation = MagicMock(spec=Reservation)
        conflicting_reservation.id = 2

        call_count = 0

        def query_side(model):
            nonlocal call_count
            mock_q = MagicMock()
            call_count += 1
            if call_count == 1:
                # Primera llamada: buscar la reserva a actualizar
                mock_q.filter.return_value.first.return_value = existing_reservation
            else:
                # Segunda llamada: verificar conflicto de mesa → hay conflicto
                mock_q.filter.return_value.first.return_value = conflicting_reservation
            return mock_q

        db.query.side_effect = query_side
        service = ReservationService(db)

        with pytest.raises(TableUnavailableError):
            service.update_reservation_status(
                reservation_id=1,
                status="confirmed",
                table_id=5
            )
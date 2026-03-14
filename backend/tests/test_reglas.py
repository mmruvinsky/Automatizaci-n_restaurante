"""
Tests de cobertura 100% de ramas — ReservationService
======================================================

Requiere: backend/conftest.py al mismo nivel que app/ y tests/.

Ejecutar:
    cd backend
    pytest tests/test_reservation_rules_full.py -v
"""

import pytest
from datetime import date, datetime, timedelta
from unittest.mock import MagicMock, patch, call
from sqlalchemy.orm import Session

from app.models import Client, Table, Reservation
from app.schemas.reservation import ReservationCreate
from app.services.reservation_service import (
    ReservationService,
    ReservationNotFoundError,
    TableUnavailableError,
    LARGE_GROUP_THRESHOLD,
    MANAGER_THRESHOLD,
)


# ─────────────────────────────────────────────────────────────────────────────
# Builders
# ─────────────────────────────────────────────────────────────────────────────

def _client(vip_level="normal", total_reservations=2):
    c = MagicMock(spec=Client)
    c.id = 1
    c.full_name = "Test Cliente"
    c.phone = "+5492614000000"
    c.email = None
    c.vip_level = vip_level
    c.total_reservations = total_reservations
    c.update_vip_level = MagicMock()
    return c


def _table(table_id=1, name="Mesa 1", capacity=4, table_type="standard", is_active=True):
    t = MagicMock(spec=Table)
    t.id = table_id
    t.name = name
    t.capacity = capacity
    t.type = table_type
    t.is_active = is_active
    return t


def _reservation_form(
    pax=2,
    event_type="normal",
    requested_cava=False,
    time_str="20:30",
    days_ahead=1,
    phone="+5492614000000",
    name="Test Cliente",
    email=None,
):
    target = date.today() + timedelta(days=days_ahead)
    return ReservationCreate(
        customer_name=name,
        customer_phone=phone,
        customer_email=email,
        date=target,
        time=time_str,
        pax=pax,
        event_type=event_type,
        requested_cava=requested_cava,
        notes=None,
    )


def _bare_res(pax, event_type="normal", requested_cava=False):
    """
    Reserva sin persistencia para probar métodos internos directamente.
    Es un MagicMock, no una instancia real de SA — no dispara descriptores.
    """
    r = MagicMock(spec=Reservation)
    r.pax = pax
    r.event_type = event_type
    r.requested_cava = requested_cava
    r.status = "pending"
    r.special_flag = False
    r.admin_notes = None
    r.table_id = None
    r.date = datetime.now() + timedelta(days=1)
    r.time = "20:30"
    r.is_event_special = event_type in ["negocios", "aniversario", "celebracion"]
    return r


def _build_db(client, tables, reservation_conflicts=None):
    """
    Session mockeada que replica las queries del servicio.

    IMPORTANTE: db.refresh no tiene side_effect.
    create_reservation crea un Reservation() real (instancia SA).
    Asignar obj.client o obj.table sobre esa instancia dispara los
    descriptores de relación de SQLAlchemy, que buscan _sa_instance_state
    en la sesión. Como la sesión es un MagicMock, no lo tiene → AttributeError.
    La solución es dejar db.refresh como un MagicMock puro sin side_effect,
    y en los tests del orquestador verificar solo atributos de columna
    (status, table_id, pax, special_flag, admin_notes), nunca relaciones.
    """
    db = MagicMock(spec=Session)
    conflicts = reservation_conflicts or []

    cava_tables = [t for t in tables if t.type == "cava" and t.is_active]
    standard_tables = sorted(
        [t for t in tables if t.type == "standard" and t.is_active],
        key=lambda t: t.capacity,
    )

    def query_side(model):
        q = MagicMock()
        if model == Client:
            q.filter.return_value.first.return_value = client
        elif model == Table:
            inner = MagicMock()
            inner.first.return_value = cava_tables[0] if cava_tables else None
            inner.order_by.return_value.all.return_value = standard_tables
            q.filter.return_value = inner
        elif model == Reservation:
            inner = MagicMock()
            inner.first.return_value = conflicts[0] if conflicts else None
            q.filter.return_value = inner
        return q

    db.query.side_effect = query_side
    db.add = MagicMock()
    db.flush = MagicMock()
    db.commit = MagicMock()
    db.refresh = MagicMock()   # sin side_effect — no toca el objeto
    return db


def _service(client, tables, conflicts=None):
    db = _build_db(client, tables, conflicts)
    return ReservationService(db), db


# ─────────────────────────────────────────────────────────────────────────────
# _apply_business_rules — R1, R2, R3
# ─────────────────────────────────────────────────────────────────────────────

class TestApplyBusinessRules:

    # [R1] pax > MANAGER_THRESHOLD (>15) ──────────────────────────────────────

    def test_R1_pax_gt_15_status_pending_special_true(self):
        client = _client()
        svc, _ = _service(client, [])
        r = _bare_res(MANAGER_THRESHOLD + 1)

        svc._apply_business_rules(r, client)

        assert r.status == "pending"
        assert r.special_flag is True

    def test_R1_admin_notes_mention_grupo_grande_or_manual(self):
        client = _client()
        svc, _ = _service(client, [])
        r = _bare_res(MANAGER_THRESHOLD + 1)

        svc._apply_business_rules(r, client)

        assert r.admin_notes is not None
        note = r.admin_notes.lower()
        assert "grupo grande" in note or "encargado" in note or "manual" in note

    def test_R1_admin_notes_include_pax_count(self):
        client = _client()
        svc, _ = _service(client, [])
        pax = 20
        r = _bare_res(pax)

        svc._apply_business_rules(r, client)

        assert str(pax) in r.admin_notes

    # [R2] pax > LARGE_GROUP_THRESHOLD and <= MANAGER_THRESHOLD (5–15) ────────

    def test_R2_pax_5_status_pending_special_true(self):
        client = _client()
        svc, _ = _service(client, [])
        r = _bare_res(LARGE_GROUP_THRESHOLD + 1)

        svc._apply_business_rules(r, client)

        assert r.status == "pending"
        assert r.special_flag is True

    def test_R2_admin_notes_mention_mesa_especial_or_cocina(self):
        client = _client()
        svc, _ = _service(client, [])
        r = _bare_res(LARGE_GROUP_THRESHOLD + 1)

        svc._apply_business_rules(r, client)

        assert r.admin_notes is not None
        note = r.admin_notes.lower()
        assert "mesa especial" in note or "cocina" in note

    def test_R2_pax_15_boundary_is_R2_not_R1(self):
        """pax=15 entra en R2 — la nota habla de mesa especial, no de encargado."""
        client = _client()
        svc, _ = _service(client, [])
        r = _bare_res(MANAGER_THRESHOLD)

        svc._apply_business_rules(r, client)

        assert r.special_flag is True
        note = r.admin_notes.lower()
        assert "mesa especial" in note or "cocina" in note

    def test_R2_admin_notes_include_pax_count(self):
        client = _client()
        svc, _ = _service(client, [])
        pax = 8
        r = _bare_res(pax)

        svc._apply_business_rules(r, client)

        assert str(pax) in r.admin_notes

    # [R3] pax <= LARGE_GROUP_THRESHOLD (<=4) ─────────────────────────────────

    def test_R3_pax_4_status_pending_special_false_no_notes(self):
        client = _client()
        svc, _ = _service(client, [])
        r = _bare_res(LARGE_GROUP_THRESHOLD)

        svc._apply_business_rules(r, client)

        assert r.status == "pending"
        assert r.special_flag is False
        assert r.admin_notes is None

    def test_R3_pax_1_special_false(self):
        client = _client()
        svc, _ = _service(client, [])
        r = _bare_res(1)

        svc._apply_business_rules(r, client)

        assert r.special_flag is False

    # Fronteras exactas ────────────────────────────────────────────────────────

    def test_boundary_pax_4_vs_5(self):
        client = _client()
        svc, _ = _service(client, [])

        r4 = _bare_res(4)
        svc._apply_business_rules(r4, client)
        assert r4.special_flag is False

        r5 = _bare_res(5)
        svc._apply_business_rules(r5, client)
        assert r5.special_flag is True

    def test_boundary_pax_15_vs_16_produce_different_notes(self):
        client = _client()
        svc, _ = _service(client, [])

        r15 = _bare_res(15)
        svc._apply_business_rules(r15, client)

        r16 = _bare_res(16)
        svc._apply_business_rules(r16, client)

        assert r15.admin_notes != r16.admin_notes


# ─────────────────────────────────────────────────────────────────────────────
# _assign_table — A, B1a, B1b, B2, C1, C2, D
# ─────────────────────────────────────────────────────────────────────────────

class TestAssignTable:

    # [A] pax > MANAGER_THRESHOLD ──────────────────────────────────────────────

    def test_A_pax_gt_15_returns_false_no_table(self):
        client = _client()
        svc, _ = _service(client, [_table(capacity=20)])
        r = _bare_res(MANAGER_THRESHOLD + 1)

        assigned, msg = svc._assign_table(r, client)

        assert assigned is False
        assert r.table_id is None

    def test_A_message_mentions_pax_or_encargado(self):
        client = _client()
        svc, _ = _service(client, [])
        r = _bare_res(16)

        _, msg = svc._assign_table(r, client)

        assert str(r.pax) in msg or "encargado" in msg.lower()

    # [B1a] cava disponible y existe en DB ─────────────────────────────────────

    def test_B1a_vip_cava_available_confirmed_table_set(self):
        client = _client(vip_level="vip")
        cava = _table(table_id=1, name="Cava", capacity=6, table_type="cava")
        svc, _ = _service(client, [cava])
        r = _bare_res(4, requested_cava=True)

        with patch.object(svc, "_is_cava_available", return_value=True):
            assigned, _ = svc._assign_table(r, client)

        assert assigned is True
        assert r.status == "confirmed"
        assert r.table_id == cava.id

    def test_B1a_special_event_aniversario_cava_assigned(self):
        client = _client(vip_level="normal")
        cava = _table(table_id=1, capacity=6, table_type="cava")
        svc, _ = _service(client, [cava])
        r = _bare_res(4, event_type="aniversario", requested_cava=True)

        with patch.object(svc, "_is_cava_available", return_value=True):
            assigned, _ = svc._assign_table(r, client)

        assert assigned is True
        assert r.table_id == cava.id

    def test_B1a_special_event_negocios_cava_assigned(self):
        client = _client(vip_level="normal")
        cava = _table(table_id=1, capacity=6, table_type="cava")
        svc, _ = _service(client, [cava])
        r = _bare_res(4, event_type="negocios", requested_cava=True)

        with patch.object(svc, "_is_cava_available", return_value=True):
            assigned, _ = svc._assign_table(r, client)

        assert assigned is True

    def test_B1a_special_event_celebracion_cava_assigned(self):
        client = _client(vip_level="normal")
        cava = _table(table_id=1, capacity=6, table_type="cava")
        svc, _ = _service(client, [cava])
        r = _bare_res(4, event_type="celebracion", requested_cava=True)

        with patch.object(svc, "_is_cava_available", return_value=True):
            assigned, _ = svc._assign_table(r, client)

        assert assigned is True

    def test_B1a_pax_6_exact_boundary_cava_assigned(self):
        """pax=6 es el límite máximo del bloque cava (el código compara pax <= 6)."""
        client = _client(vip_level="vip")
        cava = _table(table_id=1, capacity=6, table_type="cava")
        svc, _ = _service(client, [cava])
        r = _bare_res(6, requested_cava=True)

        with patch.object(svc, "_is_cava_available", return_value=True):
            assigned, _ = svc._assign_table(r, client)

        assert assigned is True
        assert r.table_id == cava.id

    # [B1b] _is_cava_available True pero no hay mesa cava en DB ───────────────

    def test_B1b_available_but_no_cava_table_in_db_pending_with_note(self):
        """
        La ventana horaria está libre pero no existe ninguna mesa tipo 'cava'
        en la DB. El servicio entra en el if cava_table → None → cae al else
        → pending con nota.
        """
        client = _client(vip_level="vip")
        svc, _ = _service(client, tables=[])   # sin mesa cava → Table.first() = None
        r = _bare_res(4, requested_cava=True)

        with patch.object(svc, "_is_cava_available", return_value=True):
            assigned, msg = svc._assign_table(r, client)

        assert assigned is False
        assert r.status == "pending"
        assert r.admin_notes is not None
        assert "cava" in r.admin_notes.lower() or "cava" in msg.lower()

    # [B2] cava ocupada ────────────────────────────────────────────────────────

    def test_B2_cava_unavailable_vip_pending_with_note(self):
        client = _client(vip_level="vip")
        cava = _table(table_id=1, capacity=6, table_type="cava")
        svc, _ = _service(client, [cava])
        r = _bare_res(4, requested_cava=True)

        with patch.object(svc, "_is_cava_available", return_value=False):
            assigned, _ = svc._assign_table(r, client)

        assert assigned is False
        assert r.status == "pending"
        assert r.admin_notes is not None

    def test_B2_cava_unavailable_special_event_pending(self):
        client = _client(vip_level="normal")
        cava = _table(table_id=1, capacity=6, table_type="cava")
        svc, _ = _service(client, [cava])
        r = _bare_res(3, event_type="celebracion", requested_cava=True)

        with patch.object(svc, "_is_cava_available", return_value=False):
            assigned, _ = svc._assign_table(r, client)

        assert assigned is False
        assert r.status == "pending"

    # Casos que NO entran en la rama B ─────────────────────────────────────────

    def test_pax_7_vip_requested_cava_does_not_enter_B(self):
        """pax=7 > 6: la condición AND pax<=6 falla → cae en D."""
        client = _client(vip_level="vip")
        cava = _table(table_id=1, capacity=8, table_type="cava")
        svc, _ = _service(client, [cava])
        r = _bare_res(7, requested_cava=True)

        assigned, _ = svc._assign_table(r, client)

        assert assigned is False
        assert r.table_id is None

    def test_normal_client_normal_event_requested_cava_falls_to_C(self):
        """No VIP ni evento especial → no entra en B → cae en C con mesa estándar."""
        client = _client(vip_level="normal")
        standard = _table(table_id=2, capacity=4, table_type="standard")
        svc, _ = _service(client, [standard])
        r = _bare_res(2, event_type="normal", requested_cava=True)

        assigned, _ = svc._assign_table(r, client)

        assert r.table_id == standard.id
        assert r.status == "confirmed"

    def test_vip_requested_cava_false_falls_to_C(self):
        """VIP pero requested_cava=False → condición B no se cumple → C."""
        client = _client(vip_level="vip")
        standard = _table(table_id=2, capacity=4, table_type="standard")
        svc, _ = _service(client, [standard])
        r = _bare_res(2, requested_cava=False)

        assigned, _ = svc._assign_table(r, client)

        assert r.table_id == standard.id

    # [C1] pax <= 4, mesa estándar libre ──────────────────────────────────────

    def test_C1_pax_2_standard_table_confirmed(self):
        client = _client()
        tables = [_table(table_id=5, capacity=4)]
        svc, _ = _service(client, tables)
        r = _bare_res(2)

        assigned, _ = svc._assign_table(r, client)

        assert assigned is True
        assert r.status == "confirmed"
        assert r.table_id == 5

    def test_C1_pax_4_boundary_confirmed(self):
        """pax=4 es el límite superior de C."""
        client = _client()
        tables = [_table(table_id=5, capacity=4)]
        svc, _ = _service(client, tables)
        r = _bare_res(4)

        assigned, _ = svc._assign_table(r, client)

        assert assigned is True
        assert r.status == "confirmed"

    # [C2] pax <= 4, sin mesa disponible ──────────────────────────────────────

    def test_C2_pax_2_all_tables_occupied_pending(self):
        client = _client()
        conflict = MagicMock(spec=Reservation)
        conflict.id = 99
        tables = [_table(capacity=4)]
        svc, _ = _service(client, tables, conflicts=[conflict])
        r = _bare_res(2)

        assigned, _ = svc._assign_table(r, client)

        assert assigned is False
        assert r.status == "pending"

    def test_C2_no_tables_at_all_pending(self):
        client = _client()
        svc, _ = _service(client, tables=[])
        r = _bare_res(2)

        assigned, _ = svc._assign_table(r, client)

        assert assigned is False
        assert r.status == "pending"

    # [D] 5–15 pax, sin condición cava ────────────────────────────────────────

    def test_D_pax_5_normal_client_no_cava_group_special(self):
        client = _client(vip_level="normal")
        svc, _ = _service(client, [])
        r = _bare_res(5, event_type="normal", requested_cava=False)

        assigned, msg = svc._assign_table(r, client)

        assert assigned is False
        assert r.table_id is None
        assert r.status == "pending"
        assert "grupo" in msg.lower() or "especial" in msg.lower() or "cocina" in msg.lower()

    def test_D_pax_15_boundary_group_special(self):
        """pax=15 es el límite superior de D."""
        client = _client()
        svc, _ = _service(client, [])
        r = _bare_res(15, event_type="normal", requested_cava=False)

        assigned, msg = svc._assign_table(r, client)

        assert assigned is False
        assert r.table_id is None


# ─────────────────────────────────────────────────────────────────────────────
# _is_cava_available — E1, E2, E3
# ─────────────────────────────────────────────────────────────────────────────

class TestIsCavaAvailable:

    def _db_cava(self, cava_table, conflict=None):
        db = MagicMock(spec=Session)
        call_n = {"n": 0}

        def query_side(model):
            q = MagicMock()
            call_n["n"] += 1
            inner = MagicMock()
            if model == Table:
                inner.first.return_value = cava_table
            elif model == Reservation:
                inner.first.return_value = conflict
            q.filter.return_value = inner
            return q

        db.query.side_effect = query_side
        return db

    def test_E1_no_cava_table_returns_false(self):
        """No existe ninguna mesa tipo cava activa → False."""
        db = self._db_cava(cava_table=None)
        svc = ReservationService(db)

        result = svc._is_cava_available(datetime.now() + timedelta(days=1), "20:30")

        assert result is False

    def test_E2_cava_exists_with_conflict_returns_false(self):
        """Hay mesa cava pero tiene reserva solapada → False."""
        cava = _table(table_id=1, table_type="cava")
        conflicting = MagicMock(spec=Reservation)
        conflicting.id = 5
        db = self._db_cava(cava_table=cava, conflict=conflicting)
        svc = ReservationService(db)

        result = svc._is_cava_available(datetime.now() + timedelta(days=1), "20:30")

        assert result is False

    def test_E3_cava_exists_no_conflict_returns_true(self):
        """Hay mesa cava y no hay reservas en la ventana → True."""
        cava = _table(table_id=1, table_type="cava")
        db = self._db_cava(cava_table=cava, conflict=None)
        svc = ReservationService(db)

        result = svc._is_cava_available(datetime.now() + timedelta(days=1), "20:30")

        assert result is True


# ─────────────────────────────────────────────────────────────────────────────
# _find_available_standard_table — F1, F2a, F2b, F3
# ─────────────────────────────────────────────────────────────────────────────

class TestFindAvailableStandardTable:

    def _db_standard(self, tables, conflict_sequence=None):
        """
        conflict_sequence: lista de valores devueltos por Reservation.first()
        en cada llamada sucesiva. Posición i corresponde a la mesa i en el loop.
        """
        db = MagicMock(spec=Session)
        seq = conflict_sequence or []
        res_call = {"n": 0}

        def query_side(model):
            q = MagicMock()
            if model == Table:
                inner = MagicMock()
                inner.order_by.return_value.all.return_value = sorted(
                    [t for t in tables if t.is_active],
                    key=lambda t: t.capacity,
                )
                q.filter.return_value = inner
            elif model == Reservation:
                idx = res_call["n"]
                res_call["n"] += 1
                val = seq[idx] if idx < len(seq) else None
                inner = MagicMock()
                inner.first.return_value = val
                q.filter.return_value = inner
            return q

        db.query.side_effect = query_side
        return db

    def test_F1_empty_table_list_returns_none(self):
        """Sin mesas → None inmediatamente."""
        db = self._db_standard([])
        svc = ReservationService(db)

        result = svc._find_available_standard_table(
            datetime.now() + timedelta(days=1), "20:30", pax=2
        )

        assert result is None

    def test_F2b_first_table_free_returned_immediately(self):
        """Primera mesa libre → devuelve sin seguir iterando."""
        t1 = _table(table_id=1, capacity=2)
        t2 = _table(table_id=2, capacity=4)
        db = self._db_standard([t1, t2], conflict_sequence=[None])
        svc = ReservationService(db)

        result = svc._find_available_standard_table(
            datetime.now() + timedelta(days=1), "20:30", pax=2
        )

        assert result is not None
        assert result.id == t1.id

    def test_F2a_first_occupied_second_free_returns_second(self):
        """Primera mesa ocupada → salta → segunda libre → la retorna."""
        t1 = _table(table_id=1, capacity=4)
        t2 = _table(table_id=2, capacity=4)
        conflict = MagicMock(spec=Reservation)
        conflict.id = 10
        db = self._db_standard([t1, t2], conflict_sequence=[conflict, None])
        svc = ReservationService(db)

        result = svc._find_available_standard_table(
            datetime.now() + timedelta(days=1), "20:30", pax=2
        )

        assert result is not None
        assert result.id == t2.id

    def test_F3_all_tables_occupied_returns_none(self):
        """Todas las mesas tienen conflicto → None."""
        t1 = _table(table_id=1, capacity=4)
        t2 = _table(table_id=2, capacity=4)
        conflict = MagicMock(spec=Reservation)
        conflict.id = 10
        db = self._db_standard([t1, t2], conflict_sequence=[conflict, conflict])
        svc = ReservationService(db)

        result = svc._find_available_standard_table(
            datetime.now() + timedelta(days=1), "20:30", pax=2
        )

        assert result is None

    def test_best_fit_smallest_sufficient_table_chosen(self):
        """La ordenación por capacidad asc garantiza que se elige la menor suficiente."""
        t_small = _table(table_id=10, capacity=2)
        t_mid   = _table(table_id=11, capacity=4)
        t_large = _table(table_id=12, capacity=6)
        db = self._db_standard([t_small, t_mid, t_large], conflict_sequence=[None])
        svc = ReservationService(db)

        result = svc._find_available_standard_table(
            datetime.now() + timedelta(days=1), "20:30", pax=2
        )

        assert result.id == t_small.id


# ─────────────────────────────────────────────────────────────────────────────
# _get_or_create_client — H1, H2
# ─────────────────────────────────────────────────────────────────────────────

class TestGetOrCreateClient:

    def test_H1_existing_client_returned_no_add_no_flush(self):
        """Cliente encontrado por teléfono → devuelve existente sin tocar la DB."""
        existing = _client()
        db = MagicMock(spec=Session)
        db.query.return_value.filter.return_value.first.return_value = existing
        svc = ReservationService(db)

        result = svc._get_or_create_client(
            name="Cualquier Nombre", phone="+5492614000000", email=None
        )

        assert result is existing
        db.add.assert_not_called()
        db.flush.assert_not_called()

    def test_H2_new_client_calls_add_and_flush(self):
        """Cliente no encontrado → se crea y se persiste con add + flush."""
        db = MagicMock(spec=Session)
        db.query.return_value.filter.return_value.first.return_value = None
        svc = ReservationService(db)

        svc._get_or_create_client(
            name="Nuevo Cliente", phone="+5492619999999", email="nuevo@test.com"
        )

        db.add.assert_called_once()
        db.flush.assert_called_once()

    def test_H2_created_object_has_correct_attributes(self):
        """El objeto pasado a db.add debe tener los datos del formulario."""
        db = MagicMock(spec=Session)
        db.query.return_value.filter.return_value.first.return_value = None
        svc = ReservationService(db)

        svc._get_or_create_client(
            name="Ana García", phone="+5492617777777", email="ana@test.com"
        )

        added = db.add.call_args[0][0]
        assert added.full_name == "Ana García"
        assert added.phone == "+5492617777777"
        assert added.email == "ana@test.com"

    def test_H2_new_client_without_email_accepted(self):
        db = MagicMock(spec=Session)
        db.query.return_value.filter.return_value.first.return_value = None
        svc = ReservationService(db)

        svc._get_or_create_client(
            name="Sin Email", phone="+5492618888888", email=None
        )

        added = db.add.call_args[0][0]
        assert added.email is None


# ─────────────────────────────────────────────────────────────────────────────
# update_reservation_status — G1, G2a, G2b, G3, G4, G5
# ─────────────────────────────────────────────────────────────────────────────

class TestUpdateReservationStatus:

    def _existing_res(self, res_id=1, current_table_id=None, current_admin_notes=None):
        r = MagicMock(spec=Reservation)
        r.id = res_id
        r.status = "pending"
        r.table_id = current_table_id
        r.admin_notes = current_admin_notes
        r.date = datetime.now() + timedelta(days=1)
        r.table = None
        return r

    def _db_update(self, reservation, conflict=None):
        db = MagicMock(spec=Session)
        call_n = {"n": 0}

        def query_side(model):
            q = MagicMock()
            call_n["n"] += 1
            inner = MagicMock()
            inner.first.return_value = reservation if call_n["n"] == 1 else conflict
            q.filter.return_value = inner
            return q

        db.query.side_effect = query_side
        db.commit = MagicMock()
        db.refresh = MagicMock()
        return db

    def test_G1_missing_reservation_raises_not_found(self):
        db = MagicMock(spec=Session)
        db.query.return_value.filter.return_value.first.return_value = None
        svc = ReservationService(db)

        with pytest.raises(ReservationNotFoundError):
            svc.update_reservation_status(9999, "confirmed")

    def test_G2a_table_conflict_raises_table_unavailable(self):
        res = self._existing_res()
        conflicting = MagicMock(spec=Reservation)
        conflicting.id = 2
        db = self._db_update(res, conflict=conflicting)
        svc = ReservationService(db)

        with pytest.raises(TableUnavailableError) as exc_info:
            svc.update_reservation_status(1, "confirmed", table_id=5)

        error_msg = str(exc_info.value)
        assert "5" in error_msg or "mesa" in error_msg.lower()
        assert "2" in error_msg

    def test_G2b_table_no_conflict_table_id_updated(self):
        res = self._existing_res()
        db = self._db_update(res, conflict=None)
        svc = ReservationService(db)

        updated = svc.update_reservation_status(1, "confirmed", table_id=7)

        assert updated.table_id == 7
        assert updated.status == "confirmed"

    def test_G3_table_id_none_existing_table_not_modified(self):
        """table_id=None → el servicio no entra en el bloque if table_id → table_id intacto."""
        res = self._existing_res(current_table_id=3)
        db = self._db_update(res)
        svc = ReservationService(db)

        updated = svc.update_reservation_status(1, "confirmed", table_id=None)

        assert updated.table_id == 3

    def test_G4_admin_notes_saved_when_provided(self):
        res = self._existing_res()
        db = self._db_update(res)
        svc = ReservationService(db)

        note = "Revisado por encargado el lunes"
        updated = svc.update_reservation_status(1, "confirmed", admin_notes=note)

        assert updated.admin_notes == note

    def test_G5_admin_notes_none_existing_note_not_overwritten(self):
        """admin_notes=None → el servicio no entra en el bloque if admin_notes → nota intacta."""
        res = self._existing_res(current_admin_notes="nota previa del encargado")
        db = self._db_update(res)
        svc = ReservationService(db)

        updated = svc.update_reservation_status(1, "confirmed", admin_notes=None)

        assert updated.admin_notes == "nota previa del encargado"

    def test_commit_and_refresh_always_called(self):
        res = self._existing_res()
        db = self._db_update(res)
        svc = ReservationService(db)

        svc.update_reservation_status(1, "cancelled")

        db.commit.assert_called_once()
        db.refresh.assert_called_once_with(res)

    @pytest.mark.parametrize("status", ["confirmed", "pending", "cancelled", "completed"])
    def test_all_valid_statuses_persisted(self, status):
        res = self._existing_res()
        db = self._db_update(res)
        svc = ReservationService(db)

        updated = svc.update_reservation_status(1, status)

        assert updated.status == status


# ─────────────────────────────────────────────────────────────────────────────
# create_reservation — O1 (efectos obligatorios), O2 (cliente nuevo)
# ─────────────────────────────────────────────────────────────────────────────

class TestCreateReservationOrchestrator:
    """
    Verifica los efectos secundarios del orquestador.

    Los tests de esta clase usan _build_db con db.refresh sin side_effect.
    create_reservation crea un Reservation() real (instancia SA).
    NO se accede a obj.client ni obj.table en los asserts — solo a
    atributos de columna (status, table_id, pax, special_flag, admin_notes)
    que SA maneja sin necesitar la sesión.
    """

    def _full_db(self, client, tables, conflict=None):
        return _build_db(client, tables, [conflict] if conflict else [])

    def test_O1_commit_called_once(self):
        client = _client()
        db = self._full_db(client, [_table(capacity=4)])
        svc = ReservationService(db)

        svc.create_reservation(_reservation_form(pax=2))

        db.commit.assert_called_once()

    def test_O1_refresh_called(self):
        client = _client()
        db = self._full_db(client, [_table(capacity=4)])
        svc = ReservationService(db)

        svc.create_reservation(_reservation_form(pax=2))

        db.refresh.assert_called_once()

    def test_O1_total_reservations_incremented(self):
        client = _client(total_reservations=7)
        db = self._full_db(client, [_table(capacity=4)])
        svc = ReservationService(db)

        svc.create_reservation(_reservation_form(pax=2))

        assert client.total_reservations == 8

    def test_O1_update_vip_level_called(self):
        client = _client()
        db = self._full_db(client, [_table(capacity=4)])
        svc = ReservationService(db)

        svc.create_reservation(_reservation_form(pax=2))

        client.update_vip_level.assert_called_once()

    def test_O1_last_visit_at_updated(self):
        client = _client()
        db = self._full_db(client, [_table(capacity=4)])
        svc = ReservationService(db)

        svc.create_reservation(_reservation_form(pax=2))

        assert client.last_visit_at is not None

    def test_O1_reservation_added_to_db(self):
        client = _client()
        db = self._full_db(client, [_table(capacity=4)])
        svc = ReservationService(db)

        svc.create_reservation(_reservation_form(pax=2))

        added_types = [type(a.args[0]).__name__ for a in db.add.call_args_list if a.args]
        assert "Reservation" in added_types

    def test_O2_get_or_create_client_called_with_form_data(self):
        """
        El orquestador llama a _get_or_create_client con los datos del formulario.

        No ejecutamos el flujo con un Client() real sin persistir porque
        Column(Integer, default=0) de SQLAlchemy solo aplica el default al
        hacer flush/insert en la DB — en memoria el atributo vale None, y
        client.total_reservations += 1 explotaría con None + 1.

        La responsabilidad de verificar que db.add recibe un Client cuando
        el cliente no existe ya está cubierta en TestGetOrCreateClient::test_H2.
        Acá verificamos solo que el orquestador delega correctamente.
        """
        client = _client()
        db = self._full_db(client, [_table(capacity=4)])
        svc = ReservationService(db)

        form = _reservation_form(
            pax=2,
            name="María López",
            phone="+5492615555555",
            email="maria@test.com",
        )

        with patch.object(svc, "_get_or_create_client", return_value=client) as mock_get:
            svc.create_reservation(form)

        mock_get.assert_called_once_with(
            name="María López",
            phone="+5492615555555",
            email="maria@test.com",
        )

    def test_pax_lte_4_with_available_table_confirmed(self):
        client = _client()
        db = self._full_db(client, [_table(capacity=4)])
        svc = ReservationService(db)

        reservation, _ = svc.create_reservation(_reservation_form(pax=2))

        assert reservation.status == "confirmed"

    def test_pax_gt_15_pending_no_table_assigned(self):
        client = _client()
        db = self._full_db(client, [_table(capacity=20)])
        svc = ReservationService(db)

        reservation, _ = svc.create_reservation(_reservation_form(pax=16))

        assert reservation.status == "pending"
        assert reservation.table_id is None
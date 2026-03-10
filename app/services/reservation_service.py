"""
Servicio de Reservas - Contiene toda la lógica de negocio.

Este archivo es el CEREBRO del sistema. Aquí están las reglas de negocio:
- Asignación automática de mesas
- Validación de disponibilidad
- Gestión de la cava
- Actualización de clientes VIP
"""

from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from datetime import datetime, date, time, timedelta
from typing import Optional, List, Tuple
import pytz

from app.models import Table, Client, Reservation
from app.schemas import ReservationCreate
from app.core.config import settings


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
        # 1. BUSCAR O CREAR CLIENTE
        client = self._get_or_create_client(
            name=reservation_data.customer_name,
            phone=reservation_data.customer_phone,
            email=reservation_data.customer_email
        )
        
        # 2. CREAR RESERVA INICIAL (sin mesa asignada aún)
        reservation = Reservation(
            client_id=client.id,
            date=self._parse_date_time(reservation_data.date, reservation_data.time),
            time=reservation_data.time,
            pax=reservation_data.pax,
            event_type=reservation_data.event_type,
            requested_cava=reservation_data.requested_cava,
            notes=reservation_data.notes,
            status="pending"  # Empezamos como pendiente
        )
        
        # 3. APLICAR REGLAS DE NEGOCIO
        self._apply_business_rules(reservation, client)
        
        # 4. INTENTAR ASIGNAR MESA
        assigned, message = self._assign_table(reservation, client)
        
        # 5. GUARDAR EN BASE DE DATOS
        self.db.add(reservation)
        
        # 6. ACTUALIZAR CLIENTE
        client.total_reservations += 1
        client.last_visit_at = datetime.now(self.tz)
        client.update_vip_level()
        
        self.db.commit()
        self.db.refresh(reservation)
        
        return reservation, message
    
    def _get_or_create_client(self, name: str, phone: str, email: Optional[str]) -> Client:
        """Busca un cliente por teléfono, o crea uno nuevo"""
        client = self.db.query(Client).filter(Client.phone == phone).first()
        
        if not client:
            client = Client(
                full_name=name,
                phone=phone,
                email=email
            )
            self.db.add(client)
            self.db.flush()  # Obtiene el ID sin hacer commit
        
        return client
    
    def _parse_date_time(self, date_obj: date, time_str: str) -> datetime:
        """Combina fecha y hora en un datetime con timezone"""
        hour, minute = map(int, time_str.split(':'))
        dt = datetime.combine(date_obj, time(hour, minute))
        return self.tz.localize(dt)
    
    def _apply_business_rules(self, reservation: Reservation, client: Client):
        """
        Aplica las reglas de negocio del documento.
        
        REGLAS:
        1. Reservas ≤4 pax: confirmación automática con mesa estándar
        2. Reservas 5-6 pax: notificación especial al personal
        3. Reservas >6 pax: estado pendiente y confirmación manual
        4. Eventos especiales + ≤6 pax: ofrecer cava si disponible
        5. Clientes VIP + ≤6 pax: prioridad en cava
        """
        pax = reservation.pax
        
        # REGLA 1: ≤4 pax → confirmación automática (si hay mesa)
        if pax <= 4:
            reservation.status = "pending"  # Lo confirmamos después de asignar mesa
            reservation.special_flag = False
        
        # REGLA 2: 5-6 pax → flag especial
        elif pax <= 6:
            reservation.special_flag = True
            reservation.status = "pending"
        
        # REGLA 3: >6 pax → siempre pendiente de confirmación manual
        else:
            reservation.status = "pending"
            reservation.special_flag = True
            reservation.admin_notes = "Reserva de grupo grande - requiere confirmación manual"
    
    def _assign_table(self, reservation: Reservation, client: Client) -> Tuple[bool, str]:
        """
        Intenta asignar una mesa a la reserva.
        
        PRIORIDADES:
        1. Si es VIP y pidió cava → intentar cava
        2. Si es evento especial y ≤6 pax → intentar cava
        3. Mesa estándar por capacidad
        
        Returns:
            (asignado: bool, mensaje: str)
        """
        pax = reservation.pax
        is_vip = client.vip_level == "vip"
        
        # CASO 1: Cliente VIP o evento especial + cava solicitada
        if (is_vip or reservation.is_event_special) and reservation.requested_cava and pax <= 6:
            cava_available = self._is_cava_available(reservation.date, reservation.time)
            
            if cava_available:
                cava_table = self.db.query(Table).filter(
                    Table.type == "cava",
                    Table.is_active == True
                ).first()
                
                if cava_table:
                    reservation.table_id = cava_table.id
                    reservation.status = "confirmed"
                    return True, f"Cava asignada automáticamente ({'Cliente VIP' if is_vip else 'Evento especial'})"
            
            # Si no está disponible la cava y fue solicitada
            if reservation.requested_cava:
                reservation.status = "pending"
                reservation.admin_notes = "Cliente solicita cava - verificar disponibilidad"
                return False, "Cava no disponible - reserva pendiente de confirmación"
        
        # CASO 2: Reservas ≤4 pax → mesa estándar automática
        if pax <= 4:
            standard_table = self._find_available_standard_table(
                reservation.date, 
                reservation.time, 
                pax
            )
            
            if standard_table:
                reservation.table_id = standard_table.id
                reservation.status = "confirmed"
                return True, "Mesa asignada automáticamente"
            else:
                reservation.status = "pending"
                return False, "No hay mesas disponibles - reserva pendiente"
        
        # CASO 3: Reservas 5-6 pax → requiere análisis
        if pax <= 6:
            reservation.status = "pending"
            reservation.admin_notes = "Verificar disponibilidad para 5-6 personas"
            return False, "Reserva pendiente de confirmación (5-6 personas)"
        
        # CASO 4: >6 pax → siempre manual
        reservation.status = "pending"
        reservation.admin_notes = f"Grupo grande ({pax} personas) - requiere configuración de mesas"
        return False, "Reserva pendiente - grupo grande requiere confirmación"
    
    def _is_cava_available(self, date: datetime, time: str) -> bool:
        """Verifica si la cava está disponible en una fecha/hora"""
        cava_table = self.db.query(Table).filter(
            Table.type == "cava",
            Table.is_active == True
        ).first()
        
        if not cava_table:
            return False
        
        # Buscar reservas en la cava en ese horario (±3 horas)
        time_start = date - timedelta(hours=3)
        time_end = date + timedelta(hours=3)
        
        existing_reservation = self.db.query(Reservation).filter(
            Reservation.table_id == cava_table.id,
            Reservation.date >= time_start,
            Reservation.date <= time_end,
            Reservation.status.in_(["confirmed", "pending"])
        ).first()
        
        return existing_reservation is None
    
    def _find_available_standard_table(
        self, 
        date: datetime, 
        time: str, 
        pax: int
    ) -> Optional[Table]:
        """Busca una mesa estándar disponible para la fecha/hora/capacidad"""
        # Buscar mesas con capacidad suficiente
        suitable_tables = self.db.query(Table).filter(
            Table.type == "standard",
            Table.capacity >= pax,
            Table.is_active == True
        ).order_by(Table.capacity).all()  # Ordenar por capacidad (más pequeña primero)
        
        if not suitable_tables:
            return None
        
        # Verificar disponibilidad de cada mesa
        time_start = date - timedelta(hours=3)
        time_end = date + timedelta(hours=3)
        
        for table in suitable_tables:
            # Buscar si tiene reservas en ese horario
            has_conflict = self.db.query(Reservation).filter(
                Reservation.table_id == table.id,
                Reservation.date >= time_start,
                Reservation.date <= time_end,
                Reservation.status.in_(["confirmed", "pending"])
            ).first()
            
            if not has_conflict:
                return table
        
        return None
    
    def get_reservations_by_date(self, date: date) -> List[Reservation]:
        """Obtiene todas las reservas de una fecha específica"""
        start = datetime.combine(date, time.min)
        end = datetime.combine(date, time.max)
        
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
        """Actualiza el estado de una reserva (para panel admin)"""
        reservation = self.db.query(Reservation).filter(
            Reservation.id == reservation_id
        ).first()
        
        if not reservation:
            raise ValueError("Reserva no encontrada")
        
        reservation.status = status
        
        if table_id is not None:
            reservation.table_id = table_id
        
        if admin_notes is not None:
            reservation.admin_notes = admin_notes
        
        self.db.commit()
        self.db.refresh(reservation)
        
        return reservation
"""
Script para resetear las mesas con el layout real del restaurante.

ATENCIÓN: Borra todas las mesas existentes y las recrea.
Si hay reservas activas, primero cancelalas o hacé un backup.

Ejecutar desde la carpeta backend/:
    python scripts/reset_tables.py
"""

import sys
sys.path.append('.')

from app.core.database import SessionLocal
from app.models import Table, Reservation

# ── Definición del layout real ────────────────────────────────────────────────
#
# Convención: mesa X y mesa X+100 son la MISMA mesa física, dos turnos.
# Sección SALÓN  → 1-10  (y 101-110)
# Sección CAVA   → 11    (y 111)
# Sección AFUERA → 12-21 (y 112-121)
#
# Formas:
#   - Barras (redondas): 9, 10, 14, 15
#   - Mesón (cap 6):     8
#   - Cava  (cap 6):     11
#   - Resto (cap 4)
#
# is_combinable = False para cava y mesón

TABLES = []

def make_pair(number: int, capacity: int, table_type: str = 'standard', combinable: bool = True):
    """Crea el par de mesas (turno 1 y turno 2) para una mesa física."""
    TABLES.append({
        'name':          f'Mesa {number}',
        'capacity':      capacity,
        'type':          table_type,
        'is_combinable': combinable,
        'is_active':     True,
    })
    TABLES.append({
        'name':          f'Mesa {number + 100}',
        'capacity':      capacity,
        'type':          table_type,
        'is_combinable': combinable,
        'is_active':     True,
    })

# ── SALÓN ─────────────────────────────────────────────────────────────────────
for n in range(1, 8):          # Mesa 1-7: cap 4, estándar
    make_pair(n, 4)

make_pair(8,  6, combinable=False)  # Mesa 8: el mesón, cap 6
make_pair(9,  4)                    # Mesa 9:  barra
make_pair(10, 4)                    # Mesa 10: barra

# ── CAVA ──────────────────────────────────────────────────────────────────────
make_pair(11, 6, table_type='cava', combinable=False)

# ── AFUERA ────────────────────────────────────────────────────────────────────
for n in range(12, 22):        # Mesa 12-21: cap 4, estándar
    make_pair(n, 4)
# (14 y 15 son barras pero la capacidad y tipo no cambia — solo la forma visual)


def main():
    db = SessionLocal()
    try:
        existing = db.query(Table).count()
        reservations = db.query(Reservation).filter(
            Reservation.status.in_(['confirmed', 'pending'])
        ).count()

        print("=" * 55)
        print("  RESET DE MESAS — Jamonería Miguel Martín")
        print("=" * 55)
        print(f"\n  Mesas actuales en DB:       {existing}")
        print(f"  Reservas activas/pendientes: {reservations}")

        if reservations > 0:
            print(f"\n  ⚠️  Hay {reservations} reservas activas.")
            print("  Estas reservas quedarán sin mesa asignada.")

        print(f"\n  Se crearán {len(TABLES)} mesas nuevas:")
        print("    - Salón:  20 mesas (1-10 + 101-110)")
        print("    - Cava:    2 mesas (11 + 111)")
        print("    - Afuera: 20 mesas (12-21 + 112-121)")
        print()

        confirm = input("  ¿Confirmar reset? (s/n): ").strip().lower()
        if confirm not in ['s', 'si', 'y', 'yes']:
            print("\n  Cancelado.\n")
            return

        # Desvincular reservas antes de borrar mesas
        db.query(Reservation).update({'table_id': None})

        # Borrar mesas existentes
        db.query(Table).delete()
        db.flush()

        # Crear mesas nuevas
        for t in TABLES:
            db.add(Table(**t))

        db.commit()

        print(f"\n  ✅ {len(TABLES)} mesas creadas correctamente.")
        print("\n  Distribución final:")

        created = db.query(Table).order_by(Table.name).all()
        sections = {'Salón': [], 'Cava': [], 'Afuera': []}
        for t in created:
            num_str = t.name.replace('Mesa ', '')
            if num_str.isdigit():
                num = int(num_str)
                base = num - 100 if num > 100 else num
                if base == 11:
                    sections['Cava'].append(t.name)
                elif 1 <= base <= 10:
                    sections['Salón'].append(t.name)
                else:
                    sections['Afuera'].append(t.name)

        for section, names in sections.items():
            print(f"    {section}: {', '.join(names)}")

        print()

    except Exception as e:
        print(f"\n  ❌ Error: {e}")
        db.rollback()
    finally:
        db.close()


if __name__ == '__main__':
    main()
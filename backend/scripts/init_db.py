"""
Script para inicializar la base de datos con datos de ejemplo.

Este script:
1. Crea todas las tablas
2. Inserta mesas iniciales
3. Crea algunos clientes de prueba (opcional)

Ejecutar:
    python scripts/init_db.py
"""

import sys
sys.path.append('.')

from app.core.database import engine, SessionLocal, Base
from app.models import Table, Client


def create_tables():
    """Crea todas las tablas en la base de datos"""
    print("🔨 Creando tablas...")
    Base.metadata.create_all(bind=engine)
    print("✅ Tablas creadas exitosamente")


def init_tables():
    """Inserta las mesas iniciales del restaurante"""
    db = SessionLocal()
    
    try:
        # Verificar si ya existen mesas
        existing = db.query(Table).first()
        if existing:
            print("⚠️  Ya existen mesas en la base de datos. Saltando inicialización.")
            return
        
        print("🪑 Creando mesas iniciales...")
        
        # CAVA (1 mesa de 6 personas)
        cava = Table(
            name="Cava",
            capacity=6,
            type="cava",
            is_combinable=False,
            is_active=True
        )
        db.add(cava)
        
        # MESAS ESTÁNDAR
        # Basado en capacidad de 60 personas con rotación
        # Mix de mesas de 2 y 4 personas
        
        # 10 mesas de 2 personas (20 pax)
        for i in range(1, 11):
            table = Table(
                name=f"Mesa {i}",
                capacity=2,
                type="standard",
                is_combinable=True,
                is_active=True
            )
            db.add(table)
        
        # 10 mesas de 4 personas (40 pax)
        for i in range(11, 21):
            table = Table(
                name=f"Mesa {i}",
                capacity=4,
                type="standard",
                is_combinable=True,
                is_active=True
            )
            db.add(table)
        
        db.commit()
        print("✅ Mesas creadas:")
        print("   - 1 Cava (6 pax)")
        print("   - 10 Mesas de 2 personas")
        print("   - 10 Mesas de 4 personas")
        print("   - Total capacidad: 60 personas")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        db.rollback()
    finally:
        db.close()


def init_test_clients():
    """Crea algunos clientes de prueba (opcional)"""
    db = SessionLocal()
    
    try:
        print("\n👥 Creando clientes de prueba...")
        
        # Cliente VIP (muchas reservas)
        vip = Client(
            full_name="Juan Pérez",
            phone="+5492614444444",
            email="juan@example.com",
            total_reservations=20,
            vip_level="vip",
            notes="Cliente VIP - siempre ofrecer cava"
        )
        db.add(vip)
        
        # Cliente frecuente
        frecuente = Client(
            full_name="María García",
            phone="+5492615555555",
            email="maria@example.com",
            total_reservations=8,
            vip_level="frecuente"
        )
        db.add(frecuente)
        
        # Cliente normal
        normal = Client(
            full_name="Carlos López",
            phone="+5492616666666",
            total_reservations=2,
            vip_level="normal"
        )
        db.add(normal)
        
        db.commit()
        print("✅ Clientes de prueba creados")
        
    except Exception as e:
        print(f"❌ Error creando clientes: {e}")
        db.rollback()
    finally:
        db.close()


def main():
    """Función principal"""
    print("=" * 50)
    print("🚀 INICIALIZANDO BASE DE DATOS")
    print("=" * 50)
    print()
    
    create_tables()
    print()
    init_tables()
    print()
    
    # Preguntar si quiere crear clientes de prueba
    response = input("\n¿Crear clientes de prueba? (s/n): ")
    if response.lower() in ['s', 'si', 'y', 'yes']:
        init_test_clients()
    
    print()
    print("=" * 50)
    print("✅ INICIALIZACIÓN COMPLETADA")
    print("=" * 50)
    print()
    print("📌 Próximos pasos:")
    print("   1. Configura tu archivo .env con las credenciales")
    print("   2. Ejecuta el servidor: uvicorn app.main:app --reload")
    print("   3. Visita http://localhost:8000/docs para ver la API")
    print()


if __name__ == "__main__":
    main()
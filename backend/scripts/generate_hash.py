#!/usr/bin/env python3
"""
Script para generar hash de contraseña con bcrypt puro.

Ejecutar:
    python scripts/generate_hash.py
"""

import bcrypt

def generate_hash(password: str) -> str:
    """Genera hash usando bcrypt puro"""
    password_bytes = password.encode('utf-8')
    salt = bcrypt.gensalt()
    hashed_bytes = bcrypt.hashpw(password_bytes, salt)
    return hashed_bytes.decode('utf-8')

def verify_hash(password: str, hash_str: str) -> bool:
    """Verifica un hash"""
    password_bytes = password.encode('utf-8')
    hash_bytes = hash_str.encode('utf-8')
    try:
        return bcrypt.checkpw(password_bytes, hash_bytes)
    except ValueError:
        return False

if __name__ == "__main__":
    # Generar hash para admin123
    password = "admin123"
    
    print("=" * 60)
    print("🔐 GENERADOR DE HASH - BCRYPT")
    print("=" * 60)
    
    print(f"\n📝 Contraseña: {password}")
    
    # Generar hash
    hashed = generate_hash(password)
    print(f"🔒 Hash generado:\n{hashed}\n")
    
    # Verificar que funciona
    is_valid = verify_hash(password, hashed)
    print(f"✅ Verificación: {'OK' if is_valid else 'FALLÓ'}")
    
    if is_valid:
        print("\n" + "=" * 60)
        print("📋 COPIA ESTE HASH EN auth_service.py")
        print("=" * 60)
        print(f"\nhashed_password=\"{hashed}\"")
        print("\n" + "=" * 60)
    else:
        print("\n❌ ERROR: El hash no se verificó correctamente")
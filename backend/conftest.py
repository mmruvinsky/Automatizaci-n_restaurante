"""
conftest.py — backend/
======================

Se ejecuta antes de que pytest collecte cualquier módulo de test.
Setea las variables de entorno requeridas por Settings() a nivel de módulo
(no en fixtures) para que la instanciación en config.py line 49 no falle.

IMPORTANTE: este archivo debe vivir en backend/conftest.py
(al mismo nivel que app/ y tests/).
"""

import os

# ── Variables obligatorias para que Settings() pueda instanciarse ─────────────
# Usamos setdefault para no pisar un .env real si el desarrollador lo tiene.

os.environ.setdefault("DATABASE_URL", "postgresql://test:test@localhost:5432/test_db")
os.environ.setdefault("SECRET_KEY", "test-secret-key-only-for-testing-never-use-in-prod")
os.environ.setdefault("ENVIRONMENT", "development")
os.environ.setdefault("TIMEZONE", "America/Argentina/Mendoza")
os.environ.setdefault("FRONTEND_URL", "http://localhost:3000")

# Twilio es Optional en Settings, pero lo dejamos vacío explícitamente
# para evitar que pydantic-settings lea un .env parcial del disco.
os.environ.setdefault("TWILIO_ACCOUNT_SID", "")
os.environ.setdefault("TWILIO_AUTH_TOKEN", "")
os.environ.setdefault("TWILIO_WHATSAPP_FROM", "")
os.environ.setdefault("ADMIN_WHATSAPP", "")
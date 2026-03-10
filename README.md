# 🍽️ Sistema de Reservas - Jamonería

Sistema inteligente de gestión de reservas con asignación automática de mesas, gestión de clientes VIP y notificaciones por WhatsApp.

## 📋 Características del MVP

- ✅ Formulario público de reservas
- ✅ Asignación automática de mesas según reglas de negocio
- ✅ Gestión estratégica de la cava (mesa VIP)
- ✅ Mini-CRM de clientes con niveles VIP
- ✅ Panel administrativo para gestionar reservas
- ✅ Notificaciones por WhatsApp (Twilio)
- ✅ API REST completa

## 🏗️ Arquitectura

```
Backend: Python + FastAPI + PostgreSQL + SQLAlchemy
Frontend: React + Next.js (próxima fase)
Notificaciones: Twilio WhatsApp API
```

## 📦 Instalación

### 1. Pre-requisitos

- Python 3.9+
- PostgreSQL 14+
- pip (gestor de paquetes de Python)

### 2. Clonar y configurar

```bash
# Entrar a la carpeta del backend
cd backend

# Crear entorno virtual
python -m venv venv

# Activar entorno virtual
# En Windows:
venv\Scripts\activate
# En Mac/Linux:
source venv/bin/activate

# Instalar dependencias
pip install -r requirements.txt
```

### 3. Configurar Base de Datos

```bash
# Crear base de datos en PostgreSQL
createdb reservas_jamoneria

# O usando psql:
psql -U postgres
CREATE DATABASE reservas_jamoneria;
\q
```

### 4. Configurar Variables de Entorno

```bash
# Copiar el archivo de ejemplo
cp .env.example .env

# Editar .env con tus credenciales
nano .env  # o tu editor favorito
```

**Configuración mínima en `.env`:**

```
DATABASE_URL=postgresql://usuario:password@localhost:5432/reservas_jamoneria
SECRET_KEY=tu-clave-secreta-cambiala
DEBUG=True
TIMEZONE=America/Argentina/Mendoza

# WhatsApp (opcional para empezar)
# TWILIO_ACCOUNT_SID=tu_sid
# TWILIO_AUTH_TOKEN=tu_token
```

### 5. Inicializar Base de Datos

```bash
# Ejecutar script de inicialización
python scripts/init_db.py
```

Este script:
- Crea todas las tablas
- Inserta las 21 mesas (1 cava + 20 estándar)
- Opcionalmente crea clientes de prueba

## 🚀 Ejecutar el Servidor

```bash
# Modo desarrollo (con auto-reload)
uvicorn app.main:app --reload

# O usando el archivo main.py:
python app/main.py
```

El servidor estará disponible en:
- **API**: http://localhost:8000
- **Documentación interactiva**: http://localhost:8000/docs
- **Redoc**: http://localhost:8000/redoc

## 📚 Uso de la API

### Crear una reserva

```bash
POST http://localhost:8000/reservations/

Body:
{
  "customer_name": "Juan Pérez",
  "customer_phone": "+5492614444444",
  "customer_email": "juan@example.com",
  "date": "2025-03-15",
  "time": "20:30",
  "pax": 4,
  "event_type": "aniversario",
  "requested_cava": false,
  "notes": "Alérgico a los mariscos"
}
```

### Listar reservas

```bash
GET http://localhost:8000/reservations/
GET http://localhost:8000/reservations/?date=2025-03-15
GET http://localhost:8000/reservations/?status=pending
```

### Ver todas las mesas

```bash
GET http://localhost:8000/tables/
```

## 🎯 Reglas de Negocio Implementadas

### Asignación Automática

1. **≤4 personas**: Confirmación automática con mesa estándar
2. **5-6 personas**: Flag especial, requiere verificación
3. **>6 personas**: Pendiente de confirmación manual

### Gestión de Cava

- **Clientes VIP** + ≤6 pax → Prioridad automática en cava
- **Eventos especiales** (negocios, aniversario, celebración) + ≤6 pax → Oferta de cava
- Si cava no disponible y fue solicitada → Estado pendiente + notificación admin

### Sistema VIP

- **≥15 reservas** → VIP (prioridad en cava)
- **≥5 reservas** → Frecuente
- **<5 reservas** → Normal

## 🔧 Tecnologías Explicadas

### FastAPI

Framework web moderno de Python. Ventajas:
- Rápido y eficiente
- Validación automática de datos
- Documentación automática (Swagger)
- Soporte async nativo

### SQLAlchemy

ORM (Object-Relational Mapping) para Python:
- Trabajas con objetos Python en lugar de SQL directo
- Previene SQL injection automáticamente
- Migraciones de base de datos

### Pydantic

Librería de validación de datos:
- Define estructura de datos con tipos
- Validación automática
- Mensajes de error claros

## 🌐 Configurar WhatsApp (Twilio)

### 1. Crear cuenta Twilio

1. Ir a https://www.twilio.com/
2. Crear cuenta gratuita (incluye $15 de crédito)
3. Verificar tu número de teléfono

### 2. Obtener credenciales

1. Dashboard → Account → API Keys
2. Copiar:
   - Account SID
   - Auth Token

### 3. Configurar WhatsApp Sandbox

1. Ir a Messaging → Try it out → Send a WhatsApp message
2. Seguir instrucciones para conectar tu WhatsApp
3. Copiar el número de sandbox (ej: +14155238886)

### 4. Actualizar .env

```
TWILIO_ACCOUNT_SID=tu_account_sid
TWILIO_AUTH_TOKEN=tu_auth_token
TWILIO_WHATSAPP_FROM=whatsapp:+14155238886
ADMIN_WHATSAPP=whatsapp:+5492614444444
```

## 📱 Próximos Pasos

### Fase 2: Frontend (React)
- Formulario público de reservas
- Panel de administración
- Calendario visual de reservas

### Fase 3: Mejoras
- Autenticación de usuarios
- Dashboard con métricas
- Exportar reportes
- Recordatorios automáticos

## 🐛 Troubleshooting

### Error de conexión a PostgreSQL

```bash
# Verificar que PostgreSQL esté corriendo
# Windows:
net start postgresql

# Mac:
brew services start postgresql

# Linux:
sudo systemctl start postgresql
```

### Error "ModuleNotFoundError"

```bash
# Verificar que el entorno virtual esté activado
# Debe aparecer (venv) al inicio del prompt

# Si no está activado:
source venv/bin/activate  # Mac/Linux
venv\Scripts\activate     # Windows
```

### Error en WhatsApp

Si WhatsApp no funciona:
1. Verifica que las credenciales en `.env` sean correctas
2. Verifica que el número de destino esté en formato internacional (+549...)
3. En sandbox, solo puedes enviar a números verificados

## 📞 Soporte

Si tienes dudas sobre el código, pregunta! Estoy aquí para explicarte cualquier parte.

## 📄 Licencia

Proyecto privado - Jamonería Miguel Martín
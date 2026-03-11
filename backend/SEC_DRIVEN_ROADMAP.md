# SEC-Driven Dev: diagnóstico y opciones de evolución

Este documento resume el estado actual del backend de reservas y propone rutas de evolución con enfoque **Security-Driven Development (SEC-Driven Dev)**.

## 1) Diagnóstico rápido del estado actual

### Fortalezas
- El dominio principal está modelado (clientes, mesas, reservas) y existe una capa de servicio para reglas de negocio de asignación.  
- Hay validaciones de entrada para reservas (fecha, horario, tipo de evento, teléfono).  
- El README define claramente el MVP, reglas de negocio y fases futuras.

### Falencias críticas (prioridad alta)
1. **No hay autenticación/autorización en endpoints administrativos** (`/tables`, actualización de estados, etc.).
2. **Manejo genérico de excepciones** que oculta errores reales y puede romper el control HTTP en runtime.
3. **Dependencia de validaciones solo a nivel API** (faltan restricciones fuertes en DB para proteger consistencia).
4. **Sin estrategia de seguridad operativa**: rate limiting, auditoría, trazabilidad, hardening de CORS, etc.
5. **Riesgo de deriva de código** por duplicación de estructura (`app/` y `backend/app/`) en el repositorio.

## 2) Evidencias concretas (código actual)

- Endpoints administrativos sin control de acceso:
  - CRUD de mesas abierto en `backend/app/api/tables.py`.
  - Cambio de estado de reservas en `backend/app/api/reservation.py`.

- Error de sombreado de nombre (`status`):
  - En `update_reservation_status`, el parámetro `status: str` colisiona con `from fastapi import ... status`.
  - En los `except`, se usa `status.HTTP_404_NOT_FOUND` y `status.HTTP_400_BAD_REQUEST`, lo que puede fallar porque `status` ahí es un `str`.

- Captura excesiva de excepciones:
  - `create_reservation` atrapa `Exception` global y responde 400 para todo.

- CORS abierto sin estrategia por entorno:
  - `allow_methods=["*"]`, `allow_headers=["*"]` en `backend/app/main.py`.

- Reglas de negocio implementadas, pero sin controles de concurrencia transaccional explícitos:
  - Asignación de mesa y verificación de conflictos en `backend/app/services/reservation_service.py`.

## 3) Opciones concretas para continuar

## Opción A — "Blindar primero" (recomendada)
Objetivo: pasar de MVP funcional a MVP seguro y operable.

### Sprint A1 (1 semana)
- Implementar autenticación JWT + rol `admin`.
- Proteger endpoints de administración:
  - `POST/PUT/DELETE /tables`
  - `PATCH /reservations/{id}/status`
- Corregir colisión de `status` en endpoint.
- Reemplazar `except Exception` por excepciones de dominio + HTTPException bien clasificadas.

### Sprint A2 (1 semana)
- Añadir rate limit por IP/teléfono en creación de reservas.
- Auditoría mínima: tabla/evento de cambios de estado y asignación manual.
- Endurecer CORS por ambiente (dev/staging/prod).

### Sprint A3 (1 semana)
- Tests de seguridad y regresión (authz, abuso, errores esperados).
- Revisar fugas de información en mensajes de error.

## Opción B — "Escalar operación"
Objetivo: optimizar operación del negocio (sin perder seguridad base).

- Estado operacional de mesas en tiempo real.
- Vista calendario de ocupación por ventana horaria.
- SLA de respuesta para reservas pendientes.
- Métricas: tasa de confirmación automática, ocupación, no-shows.

> Esta opción conviene **después** de Opción A1/A2.

## Opción C — "Producto comercial"
Objetivo: preparar el sistema para crecimiento y monetización.

- Multi-sucursal (branch_id en dominio).
- Políticas por sucursal (horarios, capacidad, cava, reglas VIP).
- Webhooks/integraciones externas (CRM, POS, BI).

> Conviene tomarla cuando ya exista base sólida de seguridad y observabilidad.

## 4) Backlog SEC-Driven Dev (orden sugerido)

1. **AuthN/AuthZ admin** (bloqueante).
2. **Fix del bug `status` + errores tipados**.
3. **Rate limiting + antifraude básico**.
4. **Constraints en DB** (unicidad lógica y checks de dominio).
5. **Logs estructurados + auditoría de decisiones automáticas/manuales**.
6. **Pruebas automatizadas por riesgo** (priorizar casos de abuso y consistencia).

## 5) Métrica de éxito por etapa

- Seguridad:
  - 100% endpoints admin protegidos.
  - 0 endpoints críticos sin autorización.
- Confiabilidad:
  - 0 errores 500 en flujos esperados de reservas.
  - Cobertura de tests para reglas de negocio críticas.
- Operación:
  - Tiempo medio de confirmación de reservas pendientes.
  - Disminución de conflictos de mesa.

## 6) Recomendación final

Si no sabes por dónde avanzar, toma esta secuencia:
1) Opción A1 (auth + corrección de errores críticos),
2) Opción A2 (controles antiabuso + auditoría),
3) recién ahí Opción B (operación) y Opción C (escala).

En SEC-Driven Dev, la regla es: **primero reducimos superficie de riesgo, luego aceleramos features**.

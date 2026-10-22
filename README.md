# Patrones de diseño implementados en el proyecto

- Factory — La clase AccountDetailFormFactory (en forms.py) encapsula la selección del formulario de detalle según el tipo de cuenta (por ejemplo, tarjeta de crédito). Permite agregar tipos de cuenta futuros con sus propios campos registrando su formulario en un solo punto, sin modificar las vistas.

- Strategy — En shared_expenses.py,en (en core/services), el reparto de un gasto compartido entre participantes se modela con una interfaz SplitStrategy y su implementación EqualSplitStrategy (reparto igualitario en centavos exactos). SplitStrategyFactory resuelve qué estrategia usar según el método de división elegido. Esto deja preparado el sistema para agregar métodos de reparto futuros (por porcentajes, montos personalizados) sin tocar la lógica de creación del gasto compartido.

- Facade — La clase FinanceFacade (en core/services/facade.py) unifica el acceso a los servicios  
de cálculo de saldos, tarjetas de crédito, reportes e importación/exportación CSV, que antes las vistas importaban directamente desde distintos módulos. Simplifica la dependencia de la capa de presentación hacia la lógica de negocio.

# FinTrack

## Pila de transacciones (LIFO)

`core/services/transaction_stack.py` implementa una pila enlazada real:
`push()` apila un identificador, `peek()` consulta el tope y `pop()` lo desapila.
Las tres operaciones tienen coste O(1). No utiliza una cola ni ordena por fecha.

`build_transaction_stack(user)` reconstruye la pila en memoria con los registros
de ese usuario, desde el primero al último insertado (coste O(n)). La base de
datos conserva los elementos entre peticiones; no se comparte una pila global.
El ID inmutable determina la inserción, incluso si se modifica la fecha contable.

La web y la API llaman a `delete_transaction()`: comprueba el tope, ejecuta
`pop()`, revierte el efecto sobre deudas, metas y pagos compartidos, y elimina
ese registro dentro de una transacción de base de datos. Las altas y bajas
bloquean la misma fila de usuario para serializar pushes y pops en motores con
bloqueo de filas. No se necesita una migración adicional.

Si registras A, luego B y después C con una fecha antigua, el orden de
eliminación es C → B → A. Los filtros no cambian el tope. La lista se muestra
en orden de registro. Un gasto compartido que tenga una transacción anterior
al tope tampoco puede borrarse hasta retirar los movimientos posteriores.


Aplicación web de gestión financiera personal construida con **Django 5.2 LTS** y **Django REST Framework**.

## Características

- Autenticación con usuario extendido (`AbstractUser`, email único)
- Registro, login, logout y recuperación de contraseña por email
- API REST con JWT opcional
- Modelos: User, Account, Category, Transaction, Budget, Tag, Attachment
- Dashboard con saldos, gráficas Chart.js (ingresos vs gastos, distribución por categoría)
- CRUD completo para cuentas, categorías, presupuestos y transacciones
- Importación/exportación CSV con detección de duplicados por hash
- Adjuntos en transacciones con validación de tipo y tamaño
- Reconciliación de transacciones
- Reportes CSV y PDF
- Documentación API con Swagger y ReDoc
- Tests, linting (black, isort, flake8) y pre-commit

## Requisitos

- Python 3.11+
- pip

## Instalación rápida (Windows PowerShell)

```powershell
cd Projects\fintrack
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
python manage.py migrate
python manage.py setup_demo
python manage.py createsuperuser
python manage.py runserver
```

`setup_demo` crea (si no existe) el usuario **demo@fintrack.local** / **demo1234**, junto con doce meses móviles de ingresos, gastos, transferencias y presupuestos. Incluye cuentas, categorías, deudas, metas y gastos compartidos pendientes, parciales y completados. Es idempotente: puedes correrlo varias veces sin duplicar datos.

## Instalación (Linux/macOS)

```bash
cd Projects/fintrack
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python manage.py migrate
python manage.py setup_demo
python manage.py createsuperuser
python manage.py runserver
```

## Scripts de ayuda

```powershell
# Windows
.\scripts\setup.ps1
.\scripts\run_dev.ps1
```

```bash
# Linux/macOS
chmod +x scripts/setup.sh scripts/run_dev.sh
./scripts/setup.sh
./scripts/run_dev.sh
```

## Variables de entorno (`.env`)

| Variable | Descripción |
| --- | --- |
| `SECRET_KEY` | Clave secreta de Django. Cambiar por un valor aleatorio propio en producción. |
| `DEBUG` | Modo debug de Django (`True`/`False`). |
| `ALLOWED_HOSTS` | Hosts permitidos, separados por coma. |
| `CSRF_TRUSTED_ORIGINS` | Orígenes de confianza para CSRF, separados por coma. |
| `DATABASE_URL` | **No tiene efecto todavía**: la base de datos está fija a SQLite (`db.sqlite3`) en `fintrack/settings.py`. Esta variable queda reservada para una futura migración a otro motor. |
| `EMAIL_BACKEND`, `EMAIL_HOST`, `EMAIL_PORT`, `EMAIL_USE_TLS`, `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD`, `DEFAULT_FROM_EMAIL` | Configuración de envío de correo (recuperación de contraseña). En desarrollo se usa el backend de consola por defecto. |
| `SITE_NAME`, `SITE_URL` | Nombre y URL del sitio, usados en plantillas de email. |
| `JWT_ENABLED` | Habilita/deshabilita la autenticación JWT en la API (`True`/`False`). La autenticación por sesión siempre está disponible. |
| `JWT_ACCESS_TOKEN_LIFETIME_MINUTES` | Minutos de vida del access token JWT. |
| `JWT_REFRESH_TOKEN_LIFETIME_DAYS` | Días de vida del refresh token JWT. |
| `MAX_ATTACHMENT_SIZE_MB` | Tamaño máximo permitido para adjuntos de transacciones. |
| `ALLOWED_ATTACHMENT_TYPES` | Tipos MIME permitidos para adjuntos, separados por coma. |

> **CORS**: `CORS_ALLOWED_ORIGINS` no se lee desde `.env` — está definido directamente en `fintrack/settings.py`. Si vas a integrar un frontend en otro dominio, edita ese setting.

## Solución de problemas

- **PowerShell no permite activar el entorno virtual** (`Activate.ps1` bloqueado):
  ```powershell
  Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
  .\.venv\Scripts\Activate.ps1
  python --version
  ```
- **Linux/macOS: "Permission denied" al ejecutar los scripts**: dales permisos de ejecución antes de correrlos:
  ```bash
  chmod +x scripts/setup.sh scripts/run_dev.sh
  ```

## URLs principales

| Recurso | URL |  |  |  |
| --- | --- | --- | --- | --- |
| Dashboard | http://127.0.0.1:8000/ |  |  |  |
| Admin | http://127.0.0.1:8000/admin/ |  |  |  |
| Swagger API | http://127.0.0.1:8000/api/docs/ |  |  |  |
| ReDoc API | http://127.0.0.1:8000/api/redoc/ |  |  |  |
| Schema OpenAPI | http://127.0.0.1:8000/api/schema/ |  |  |  |

## API JWT (opcional)

Habilitado por defecto (`JWT_ENABLED=True` en `.env`).

```bash
# Obtener token (usar email como username; con el usuario creado por setup_demo)
curl -X POST http://127.0.0.1:8000/api/auth/token/ \
  -H "Content-Type: application/json" \
  -d '{"email": "demo@fintrack.local", "password": "demo1234"}'

# Usar token
curl http://127.0.0.1:8000/api/accounts/ \
  -H "Authorization: Bearer <access_token>"
```

## Paginación y filtros de la API

Los listados de la API usan paginación por número de página, con 20 elementos por página (`PAGE_SIZE = 20`). La respuesta incluye `count`, `next`, `previous` y `results`.

El endpoint de transacciones (`/api/transactions/`) además soporta:

- **Filtros exactos**: `?account=<id>`, `?category=<id>`, `?transaction_type=income|expense|transfer`, `?is_reconciled=true|false`, `?date=YYYY-MM-DD`.
- **Búsqueda de texto**: `?search=<texto>` (busca en descripción y notas).
- **Ordenamiento**: `?ordering=date` / `?ordering=-amount` / `?ordering=created_at`.

## Importación CSV

Formato esperado:

```csv
date,account,category,transaction_type,amount,description,notes
2026-03-01,Cuenta Principal,Comida,expense,150.00,Supermercado,
```

Los duplicados se detectan por hash SHA-256 de fecha + cuenta + monto + descripción.

## Tests y calidad de código

```bash
pytest
black .
isort .
flake8 .
pre-commit install
pre-commit run --all-files
```

> Actualmente no hay medición de cobertura configurada (`pytest-cov` no está en `requirements.txt`).

## Despliegue / producción

Usa el perfil `fintrack.production`, la plantilla `.env.production.example` y
la guía [PRODUCCION.md](PRODUCCION.md) para desplegar con HTTPS, cookies seguras,
WhiteNoise y Waitress. La base de datos pública debe estar separada de la demo.

Antes de desplegar en producción:

1. Genera un `SECRET_KEY` propio y aleatorio.
2. Configura `DEBUG=False`, `ALLOWED_HOSTS` y `CSRF_TRUSTED_ORIGINS` con tus dominios reales.
3. Ejecuta `python manage.py collectstatic` para recolectar los estáticos en `STATIC_ROOT`.
4. Sirve la app con un servidor WSGI/ASGI real (por ejemplo Gunicorn apuntando a `fintrack.wsgi:application`, o Uvicorn/Daphne a `fintrack.asgi:application`), no con `runserver`.

## Estructura del proyecto

```
fintrack/
├── fintrack/          # Configuración Django
├── core/              # App principal
│   ├── api/           # REST API
│   ├── services/      # Lógica de negocio
│   ├── fixtures/      # Datos de ejemplo
│   └── tests/
├── templates/
├── static/
├── scripts/
├── requirements.txt
└── manage.py
```

## Licencia

MIT (pendiente añadir el archivo `LICENSE` en la raíz del repositorio).

# 📚 Documentación del código

La documentación del código fuente está generada con Sphinx y se encuentra en la carpeta `docs/build/html/`.

### Cómo ver la documentación

**Opción 1 (recomendada):**
1. Abra la carpeta `docs/build/html/`
2. Haga doble clic en `index.html`
3. Se abrirá en su navegador web

**Opción 2 (con servidor local):**
```bash
cd docs/build/html/
python -m http.server 8000
# Abrir http://localhost:8000 en su navegador

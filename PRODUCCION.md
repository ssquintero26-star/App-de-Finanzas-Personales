# Despliegue de FinTrack

El perfil local sigue funcionando en HTTP. El perfil `fintrack.production`
desactiva la depuración, exige una clave secreta y dominios explícitos,
protege las cookies, fuerza HTTPS y sirve los archivos estáticos con WhiteNoise.
Usa Django 5.2 LTS y Waitress; no uses `runserver` como servidor público.

## Preparación

1. Instala Python 3.12 y crea un entorno: `python -m venv .venv`.
2. Instala las dependencias con `.venv\Scripts\python -m pip install -r requirements.txt`.
3. Copia `.env.production.example` a `.env`. Configura una `SECRET_KEY` aleatoria
   de al menos 50 caracteres, tu dominio, origen HTTPS y credenciales SMTP.
   Puedes generar la clave con `python -c "import secrets; print(secrets.token_urlsafe(64))"`.
4. Establece `DJANGO_SETTINGS_MODULE=fintrack.production` en el entorno del servicio.
5. Con una copia de seguridad de la base de datos, ejecuta:

   ```powershell
   .venv\Scripts\python manage.py migrate --noinput
   .venv\Scripts\python manage.py collectstatic --noinput
   .venv\Scripts\python manage.py check --deploy
   .venv\Scripts\python -m pytest
   ```

6. Inicia `scripts\run_production.ps1` desde un servicio supervisado.
   En Linux puedes usar `.venv/bin/waitress-serve --listen=127.0.0.1:8000 fintrack.wsgi:application`.
7. Configura un proxy inverso con certificado HTTPS, límites de carga y logs.
   Waitress escucha únicamente en localhost. Activa `TRUST_PROXY_HTTPS` solo
   cuando el proxy sobrescriba `X-Forwarded-Proto` y no acepte valores del cliente.

## Datos y operación

- La configuración incluida utiliza SQLite. Mantén una única instancia de la app,
  respaldos consistentes con la API de backup de SQLite y almacenamiento persistente.
  Antes de un despliegue con múltiples instancias o alta concurrencia, configura y
  valida PostgreSQL, incluidos sus respaldos y la restauración.
- No cargues `setup_demo` en una base de datos con información real. Las cuentas
  `demo@fintrack.local`, `juan@fintrack.local` y `maria@fintrack.local` usan una
  contraseña pública de ejemplo. El servidor de producción debe usar una base
  de datos limpia, usuarios reales y una cuenta administradora propia.
- Los comprobantes se descargan por una vista autenticada que comprueba el dueño.
  Mantén `media/` en almacenamiento persistente y no publiques esa carpeta en
  Nginx, IIS ni otro servidor como recurso anónimo.
- Prueba recuperación de contraseña con el SMTP real y monitoriza errores 500,
  espacio disponible, respaldos y vencimiento del certificado.
- Las advertencias HSTS sobre subdominios y precarga requieren una decisión del
  dominio: no se activan automáticamente para no bloquear subdominios sin HTTPS.
- Verifica dependencias y avisos de seguridad al desplegar; el archivo de requisitos
  permite recibir parches dentro de la rama LTS.

## Recorrido para la demo local

Ejecuta `python manage.py migrate` y `python manage.py setup_demo`, luego abre
la app e inicia sesión con `demo@fintrack.local` / `demo1234`.
La carga conserva los registros existentes y agrega doce meses móviles sin
duplicados. Incluye ingresos, gastos, transferencias a ahorros, presupuestos,
metas, deudas y gastos compartidos con los tres estados.

Muestra el flujo mensual del dashboard, los presupuestos del mes, los filtros de
transacciones y el único enlace Eliminar habilitado. Abre Cena grupo Cartagena
para mostrar participantes e historial; registra un pago en un gasto pendiente.
Prueba además crear una transacción, conciliarla y exportar CSV/PDF.

Estas comprobaciones locales no sustituyen la validación del dominio, TLS, correo,
restauración de respaldos y capacidad del servidor de destino.

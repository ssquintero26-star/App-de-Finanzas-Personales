# Validación de FinTrack

Fecha: 21 de octubre de 2026. Entorno local Windows, Python 3.12 y Django 5.2.18.

## Correcciones

- Restauradas las marcas de tiempo de transacciones, participantes y pagos.
  La migración 0017 conserva los registros existentes. Resuelve el error
  `SharedExpensePayment.created_at`, la conciliación y las reversiones de pagos.
- Restablecida la función pública de reparto equitativo para ejecutar la suite.
- Corregida la edición de transacciones asociadas a metas y deudas: se valida
  el saldo sin contar dos veces el movimiento anterior y se actualiza la relación
  después de revertir el efecto anterior.
- Los pagos vuelven a consultar el pendiente dentro de una transacción de base
  de datos. Rechazan sobrepagos, montos no positivos y cuentas ajenas o inactivas.
  Los errores de negocio de la API responden con 400.
- Los comprobantes requieren autenticación y pertenencia al usuario. Sus URLs
  directas de media ya no se publican por Django.
- CSV rechaza montos no finitos, negativos, con exceso de decimales o fuera del
  rango permitido. Un archivo con codificación inválida muestra un error legible.
- La página de registrar pagos redirige al login cuando no hay sesión.
- El cierre de sesión utiliza POST con CSRF, compatible con Django 5.2.
- La documentación de la API se genera sin errores de usuario anónimo ni
  advertencias de tipos de los campos calculados.
- Los gráficos se sirven desde el proyecto. Se eliminaron referencias a mapas
  de depuración que no estaban incluidos y bloqueaban la preparación de estáticos.

## Demo

`setup_demo` agrega doce meses móviles de datos sin duplicar registros.
En la base local se añadieron 108 movimientos mensuales, presupuestos de comida,
transporte y servicios, una deuda, una meta y tres gastos compartidos con estados
pendiente, parcial y completado. Se conservó el contenido anterior.

Se verificó en el navegador el detalle de Cena grupo Cartagena, sus participantes
e historial de pagos, y el gráfico del flujo de seis meses con ingresos y gastos.
La copia de seguridad anterior a la migración y a la carga está en `backups/`.

## Comprobaciones

- Suite completa, incluida la pila: **217 pruebas aprobadas**, sin fallos,
  en Python 3.12 y Django 5.2.18. Resultado guardado en `qa-stack-full.log`.
- El recorrido de demo prueba login, dashboard, listas, formularios, detalles,
  exportación CSV/PDF, API y cierre de sesión. También prueba que repetir la carga
  no cambie los conteos.
- Las regresiones cubren eliminación de la última transacción, filtros,
  aislamiento por usuario, sobrepagos con objetos desactualizados, edición de
  metas completadas y descarga privada de comprobantes.
- `makemigrations --check --dry-run`: sin cambios pendientes.
- `collectstatic`: completado con almacenamiento de producción y nombres con hash.
- Perfil de producción: redirección HTTP a HTTPS, login por HTTPS, cookie CSRF
  segura y descarga de la librería de gráficos comprobados.
- `pip check`: sin incompatibilidades entre dependencias instaladas.
- Servidor local reiniciado y comprobado con respuesta HTTP 200.
- Segunda carga sobre la base local: cero movimientos nuevos; sin duplicados.
- `check --deploy`: dos advertencias opcionales sobre HSTS en subdominios y
  precarga. Requieren confirmar las condiciones del dominio antes de activarlas.

## Alcance de producción

Se prepararon `fintrack.production`, `.env.production.example`, un lanzador
Waitress y [PRODUCCION.md](PRODUCCION.md). El perfil exige una clave secreta
propia y dominios explícitos; desactiva DEBUG y activa protecciones HTTPS.

La validación realizada es funcional y de configuración local. No se ha
publicado la app ni probado un servidor externo. Antes de abrirla al público
deben configurarse dominio y certificado, SMTP, supervisión del proceso,
respaldos con restauración probada y una base de datos separada de la demo.
La configuración SQLite incluida está orientada a una única instancia;
un despliegue concurrente con varias instancias requiere PostgreSQL y pruebas
de carga sobre esa infraestructura.

## Pila LIFO de transacciones

`TransactionStack` es una pila enlazada con operaciones `push`, `peek` y `pop`
O(1). Se reconstruye por usuario desde los IDs en orden de inserción; reconstruir
la pila cuesta O(n). No depende de la fecha contable ni de fechas de creación
editables, y no se conserva estado global entre peticiones.

La eliminación web y API usa un servicio común que comprueba el tope, ejecuta
`pop`, revierte los efectos financieros y borra la transacción de forma atómica.
Las altas y bajas bloquean la misma fila de usuario en motores con bloqueo de
filas. La lista muestra primero la última registrada. Eliminar un gasto compartido
también respeta la pila cuando tiene una transacción asociada.

Las pruebas específicas cubren LIFO, pila vacía, reconstrucción, aislamiento por
usuario, fechas antiguas o modificadas, confirmaciones desactualizadas, reversión
de saldos ante errores y protección de gastos compartidos en web y API.
No se añaden campos ni migraciones de base de datos.

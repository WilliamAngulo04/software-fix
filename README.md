# Software Fix — Gestión de servicio técnico

Aplicación web en Django para un taller de reparación de celulares y computadores: recepción de equipos,
órdenes de servicio con estados, evidencias fotográficas, inventario de repuestos y ventas.

## Roles

| Rol | Puede |
|---|---|
| **Administrador** | Todo, incluido gestionar usuarios, el inventario y el panel `/admin/` |
| **Recepcionista** | Registrar clientes y equipos, crear órdenes, asignar técnicos, cobrar y vender |
| **Técnico** | Ver órdenes, actualizar diagnóstico, estado y costos de sus órdenes (o de las que no tienen técnico), usar repuestos y subir fotos |

## Flujo de una reparación

1. **Recepción**: se registra el cliente, su equipo y se crea la orden (código automático `ORD-2026-0001`).
   Se suben fotos de *recepción* y se imprime el comprobante para el cliente.
2. **Diagnóstico y reparación**: el técnico cambia el estado (`en_diagnostico` → `esperando_aprobacion` → `en_reparacion` → `listo_entrega`),
   escribe el diagnóstico, agrega repuestos (se descuentan del inventario) y define el costo final.
3. **Entrega**: recepción pulsa **Cobrar y entregar**; se genera la venta (servicio + productos adicionales opcionales)
   y la orden pasa a `entregado` automáticamente.

## Instalación

Requisitos: Python 3.12 o superior y PostgreSQL 14 o superior.

```powershell
cd "Software fIx v2"
python -m venv venv
.\venv\Scripts\activate
pip install -r requirements.txt
```

### Configurar PostgreSQL

1. Instala PostgreSQL desde https://www.postgresql.org/download/windows/ (anota la contraseña del usuario `postgres`).
2. Crea la base de datos (desde *SQL Shell (psql)* o pgAdmin):
   ```sql
   CREATE DATABASE software_fix;
   ```
3. Copia `.env.example` como `.env` y escribe tu contraseña en `DB_PASSWORD`.

> Si `DB_NAME` queda vacío en `.env` (o no existe `.env`), la aplicación usa SQLite. Sirve para probar sin PostgreSQL.

### Crear las tablas y arrancar

```powershell
python manage.py migrate
python manage.py datos_demo        # opcional: usuarios, clientes y productos de ejemplo
python manage.py createsuperuser   # o crea tu propio administrador
python manage.py runserver
```

Abre http://127.0.0.1:8000. Con los datos de demostración puedes entrar como
`admin@softwarefix.com`, `tecnico@softwarefix.com` o `recepcion@softwarefix.com`, todos con la contraseña `Taller2026*`.

## Publicar en Vercel

Vercel detecta Django automáticamente (por `manage.py`) y ejecuta `collectstatic` en cada despliegue.
Como Vercel no tiene disco permanente ni base de datos propia, se necesitan dos servicios externos.
[Supabase](https://supabase.com) (plan gratuito) cubre ambos:

- **PostgreSQL** → variable `DATABASE_URL`
- **Almacenamiento de fotos** (compatible con S3) → variables `S3_*`

### 1. Supabase

1. Crea un proyecto en Supabase y guarda la contraseña de la base de datos.
2. **Base de datos**: botón *Connect* → *Connection string* → **Transaction pooler** (puerto 6543).
   Copia la URL y reemplaza `[YOUR-PASSWORD]` por tu contraseña. Si la contraseña tiene caracteres
   como `@ # / :`, escríbelos codificados (`@` → `%40`, `#` → `%23`).
3. **Fotos**: *Storage* → *New bucket* → nombre `evidencias`, **privado**.
   Luego *Storage* → *Settings* → *S3 Connection*: copia el *Endpoint* y la *Region*, y crea un *Access key*.

### 2. Crear las tablas en la base de la nube (desde tu PC)

Crea el archivo `.env` en esta carpeta (junto a `manage.py`) con la URL de Supabase:

```
DATABASE_URL=postgresql://postgres.xxxx:tu_contraseña@aws-0-us-east-1.pooler.supabase.com:6543/postgres
```

Y ejecuta:

```powershell
python manage.py migrate
python manage.py createsuperuser
```

### 3. Subir el código a GitHub

```powershell
git init
git add .
git commit -m "Software Fix"
git branch -M main
git remote add origin https://github.com/TU_USUARIO/software-fix.git
git push -u origin main
```

`.gitignore` ya excluye `venv/`, `.env`, la base SQLite y las fotos locales.

### 4. Importar en Vercel

1. En https://vercel.com/new importa el repositorio. El *Framework Preset* debe ser **Django**.
2. En *Environment Variables* agrega:

| Variable | Valor |
|---|---|
| `SECRET_KEY` | Una clave larga y aleatoria. Genérala con `python -c "import secrets; print(secrets.token_urlsafe(50))"` |
| `DATABASE_URL` | La URL del Transaction pooler de Supabase |
| `S3_BUCKET` | `evidencias` |
| `S3_ENDPOINT_URL` | El endpoint S3 de Supabase (`https://xxxx.storage.supabase.co/storage/v1/s3`) |
| `S3_REGION` | La región de Supabase (ej. `us-east-1`) |
| `S3_ACCESS_KEY_ID` | Access key ID |
| `S3_SECRET_ACCESS_KEY` | Secret access key |
| `TIME_ZONE` | `America/Bogota` (opcional) |

3. Pulsa **Deploy**. Cada `git push` a `main` vuelve a publicar la aplicación.

Notas:
- En Vercel `DEBUG` queda apagado automáticamente y el dominio `*.vercel.app` se autoriza solo.
  Si usas un dominio propio, agrégalo en `ALLOWED_HOSTS` y en `CSRF_TRUSTED_ORIGINS` (`https://midominio.com`).
- Vercel limita cada petición a 4,5 MB; por eso las fotos se reducen en el navegador antes de subirlas.
- Cuando cambies los modelos, ejecuta `python manage.py migrate` desde tu PC (con el `.env` apuntando a Supabase)
  antes de publicar.

## Pruebas

```powershell
python manage.py test tests
```

## Estructura

```
config/       Configuración (settings, urls)
cuentas/      Usuarios, roles, login y panel principal
clientes/     Clientes y equipos
ordenes/      Órdenes de servicio, evidencias fotográficas y repuestos usados
inventario/   Productos y repuestos
ventas/       Ventas y cobro de órdenes
templates/    Plantillas HTML (Bootstrap 5)
tests/        Pruebas automáticas
```

## Correspondencia con el esquema SQL

Las tablas conservan los nombres del diseño original: `usuarios`, `clientes`, `equipos`, `ordenes_servicio`,
`evidencias_fotograficas`, `productos_inventario`, `detalle_reparacion_repuestos`, `ventas` y `venta_detalles`.

Diferencias con el SQL original:

- **ENUM**: `estado_orden` y `tipo_momento_evidencia` se guardan como `VARCHAR` con opciones validadas por Django,
  lo que facilita agregar estados nuevos sin `ALTER TYPE`.
- **usuarios**: Django añade las columnas `last_login` e `is_superuser`, y las tablas de grupos y permisos.
- **evidencias_fotograficas.url_foto**: guarda la ruta del archivo dentro de la carpeta `media/`.

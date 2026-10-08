"""
Configuración del proyecto Software Fix.

Los valores sensibles (clave secreta, credenciales de base de datos) se leen
del archivo .env en la raíz del proyecto. Ver .env.example.
"""
import os
import urllib.parse
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / '.env')


def env_bool(name, default=False):
    return os.getenv(name, str(default)).strip().lower() in ('1', 'true', 'yes', 'si')


SECRET_KEY = os.getenv('SECRET_KEY', 'django-insecure-cambiar-esta-clave-en-produccion')
# En Vercel (variable VERCEL definida) DEBUG queda apagado salvo que se pida explícitamente.
DEBUG = env_bool('DEBUG', not os.getenv('VERCEL'))
ALLOWED_HOSTS = [h.strip() for h in os.getenv('ALLOWED_HOSTS', 'localhost,127.0.0.1').split(',') if h.strip()]

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.humanize',
    # Apps del proyecto
    'cuentas',
    'clientes',
    'inventario',
    'ordenes',
    'ventas',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'

# Base de datos, en orden de prioridad:
#   1. DATABASE_URL (PostgreSQL en la nube: Supabase, Neon… lo usa Vercel)
#   2. DB_NAME y demás variables DB_* (PostgreSQL local)
#   3. SQLite (solo para pruebas)
if os.getenv('DATABASE_URL'):
    url = urllib.parse.urlparse(os.environ['DATABASE_URL'])
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': url.path.lstrip('/'),
            'USER': urllib.parse.unquote(url.username or ''),
            'PASSWORD': urllib.parse.unquote(url.password or ''),
            'HOST': url.hostname,
            'PORT': url.port or 5432,
            'OPTIONS': {'sslmode': 'require'},
            # Necesario si la URL apunta a un pooler en modo transacción (PgBouncer / Supavisor).
            'DISABLE_SERVER_SIDE_CURSORS': True,
        }
    }
elif os.getenv('DB_NAME'):
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': os.getenv('DB_NAME'),
            'USER': os.getenv('DB_USER', 'postgres'),
            'PASSWORD': os.getenv('DB_PASSWORD', ''),
            'HOST': os.getenv('DB_HOST', 'localhost'),
            'PORT': os.getenv('DB_PORT', '5432'),
        }
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }

AUTH_USER_MODEL = 'cuentas.Usuario'
LOGIN_URL = 'login'
LOGIN_REDIRECT_URL = 'dashboard'
LOGOUT_REDIRECT_URL = 'login'

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LANGUAGE_CODE = 'es'
TIME_ZONE = os.getenv('TIME_ZONE', 'America/Bogota')
USE_I18N = True
USE_TZ = True

STATIC_URL = 'static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'

# Fotos de evidencias.
# En Vercel el disco no es persistente, así que si se define S3_BUCKET las fotos se guardan
# en un almacenamiento compatible con S3 (Supabase Storage, Cloudflare R2, AWS S3).
# El bucket puede ser privado: las URLs se firman y caducan a la hora.
MEDIA_URL = 'media/'
MEDIA_ROOT = BASE_DIR / 'media'

STORAGES = {
    'default': {'BACKEND': 'django.core.files.storage.FileSystemStorage'},
    'staticfiles': {'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage'},
}
if os.getenv('S3_BUCKET'):
    STORAGES['default'] = {
        'BACKEND': 'storages.backends.s3.S3Storage',
        'OPTIONS': {
            'bucket_name': os.environ['S3_BUCKET'],
            'endpoint_url': os.getenv('S3_ENDPOINT_URL'),
            'region_name': os.getenv('S3_REGION'),
            'access_key': os.getenv('S3_ACCESS_KEY_ID'),
            'secret_key': os.getenv('S3_SECRET_ACCESS_KEY'),
            'addressing_style': 'path',
            'signature_version': 's3v4',
            'querystring_auth': True,
            'querystring_expire': 3600,
            'file_overwrite': False,
        },
    }

# Producción (DEBUG=False): HTTPS y cookies seguras. Vercel termina TLS en su proxy.
CSRF_TRUSTED_ORIGINS = [o.strip() for o in os.getenv('CSRF_TRUSTED_ORIGINS', '').split(',') if o.strip()]
if os.getenv('VERCEL_URL'):
    ALLOWED_HOSTS.append(os.environ['VERCEL_URL'])
    CSRF_TRUSTED_ORIGINS.append(f"https://{os.environ['VERCEL_URL']}")
if os.getenv('VERCEL_PROJECT_PRODUCTION_URL'):
    ALLOWED_HOSTS.append(os.environ['VERCEL_PROJECT_PRODUCTION_URL'])
    CSRF_TRUSTED_ORIGINS.append(f"https://{os.environ['VERCEL_PROJECT_PRODUCTION_URL']}")

if not DEBUG:
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
    SECURE_SSL_REDIRECT = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_HSTS_SECONDS = 3600
    SECURE_CONTENT_TYPE_NOSNIFF = True
    if SECRET_KEY.startswith('django-insecure'):
        raise RuntimeError('Define SECRET_KEY en las variables de entorno antes de usar DEBUG=False.')

DEFAULT_AUTO_FIELD = 'django.db.models.AutoField'

"""
Datos iniciales del sistema de licencias:
- Los 4 planes (los precios son de ejemplo; el superusuario los ajusta en /admin/).
- La configuración de la plataforma.
- Los talleres que ya existían reciben los días de prueba desde hoy, para no bloquearlos de golpe.
"""
from datetime import timedelta
from decimal import Decimal

from django.db import migrations
from django.utils import timezone

PLANES = [
    ('Mensual', 30, Decimal('50000'), 1),
    ('Trimestral', 90, Decimal('135000'), 2),
    ('Semestral', 180, Decimal('250000'), 3),
    ('Anual', 365, Decimal('450000'), 4),
]


def crear(apps, schema_editor):
    PlanLicencia = apps.get_model('licencias', 'PlanLicencia')
    Configuracion = apps.get_model('licencias', 'ConfiguracionPlataforma')
    Establecimiento = apps.get_model('cuentas', 'Establecimiento')

    for nombre, dias, precio, orden in PLANES:
        PlanLicencia.objects.get_or_create(nombre=nombre, defaults={'dias': dias, 'precio': precio, 'orden': orden})
    config, _ = Configuracion.objects.get_or_create(pk=1)
    Establecimiento.objects.filter(licencia_hasta__isnull=True).update(
        licencia_hasta=timezone.now() + timedelta(days=config.dias_prueba),
    )


class Migration(migrations.Migration):
    dependencies = [
        ('licencias', '0001_initial'),
        ('cuentas', '0003_establecimiento_licencia_hasta'),
    ]

    operations = [
        migrations.RunPython(crear, migrations.RunPython.noop),
    ]

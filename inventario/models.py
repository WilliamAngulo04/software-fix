from django.db import models


class ProductoInventario(models.Model):
    """Catálogo de productos y repuestos."""

    class Categoria(models.TextChoices):
        ACCESORIO = 'accesorio', 'Accesorio'
        REPUESTO = 'repuesto', 'Repuesto'
        HERRAMIENTA = 'herramienta', 'Herramienta'

    codigo_barras = models.CharField('código de barras', max_length=50, unique=True, null=True, blank=True)
    nombre = models.CharField(max_length=120)
    categoria = models.CharField('categoría', max_length=50, choices=Categoria.choices)
    precio_compra = models.DecimalField(max_digits=10, decimal_places=2)
    precio_venta = models.DecimalField(max_digits=10, decimal_places=2)
    stock_actual = models.IntegerField(default=0)
    stock_minimo = models.IntegerField('stock mínimo', default=2)
    es_repuesto = models.BooleanField(default=False)
    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'productos_inventario'
        ordering = ['nombre']
        verbose_name = 'producto'

    def __str__(self):
        return self.nombre

    @property
    def stock_bajo(self):
        return self.stock_actual <= self.stock_minimo

AVISAR_DESDE_DIAS = 5


def licencia(request):
    """Expone el estado de la licencia del taller para el aviso en la barra superior."""
    usuario = getattr(request, 'user', None)
    if not usuario or not usuario.is_authenticated or usuario.is_superuser or not usuario.establecimiento_id:
        return {}
    taller = usuario.establecimiento
    dias = taller.dias_restantes
    return {
        'licencia_dias': dias,
        'licencia_vigente': taller.licencia_vigente,
        'licencia_en_prueba': taller.en_prueba,
        'licencia_avisar': dias <= AVISAR_DESDE_DIAS,
    }

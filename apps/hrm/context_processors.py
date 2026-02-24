"""
Context processor para exponer la sucursal actual del usuario y la lista de sucursales
disponibles en todas las plantillas.
"""
from .models import Worker, Subsidiary, Establishment


def user_subsidiary(request):
    """Añade current_subsidiary, current_worker y subsidiary_set al contexto."""
    context = {
        'current_subsidiary': None,
        'current_worker': None,
        'subsidiary_set': [],
    }
    if request.user.is_authenticated:
        try:
            worker = Worker.objects.filter(user=request.user).order_by('-id').first()
            if worker:
                context['current_worker'] = worker
                establishment = Establishment.objects.filter(worker=worker).select_related('subsidiary').last()
                if establishment and establishment.subsidiary:
                    context['current_subsidiary'] = establishment.subsidiary
        except (Worker.DoesNotExist, AttributeError):
            pass
        context['subsidiary_set'] = Subsidiary.objects.filter(is_address=False).order_by('id', 'serial')
    return context

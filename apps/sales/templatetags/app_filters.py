from django import template
from django.template.loader import get_template


register = template.Library()


@register.filter(name='zfill')
def zfill(d, k):
    res = str(d).zfill(int(k))
    return res


@register.filter(name='get_item')
def get_item(d, key):
    """Obtiene un valor de un diccionario por clave."""
    if d is None:
        return None
    return d.get(key) if hasattr(d, 'get') else None
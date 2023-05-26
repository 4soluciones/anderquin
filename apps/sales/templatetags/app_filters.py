from django import template
from django.template.loader import get_template


register = template.Library()


@register.filter(name='zfill')
def zfill(d, k):
    res = str(d).zfill(int(k))
    return res
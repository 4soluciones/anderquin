from django import template

register = template.Library()


@register.simple_tag(name='add')
def add(value1, value2):
    return value1 + value2


@register.filter
def divide(value, arg):
    try:
        return float(value) / float(arg)
    except (TypeError, ZeroDivisionError):
        return None


@register.filter
def differences(value1, value2):
    return float(value1) - float(value2)


@register.filter
def multiplication(value1, value2):
    return float(value1) * float(value2)


@register.filter(name='get')
def get(d, k):
    return d.get(k, None)


@register.filter(name='get_element')
def get_element(d, k):
    return d[k]


@register.filter(name='thousands_separator')
def thousands_separator(value):
    if value is not None and value != '':
        return '{:,}'.format(value)
    return ''


@register.filter(name='replace_round')
def replace_round(value):
    if value is not None and value != '':
        return str(round(value, 2)).replace(',', '.')
    return value

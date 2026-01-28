import decimal

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


@register.filter(name='mod_number')
def mod_number(value):
    if value is not None and value != '':
        return abs(value)
    return ''


@register.filter(name='replace_round')
def replace_round(value):
    if value is not None and value != '':
        value = float(value)
        decimal_part = value - int(value)
        decimal_str = f"{decimal_part:.3f}"[2:]
        if int(decimal_str[2]) > 0:
            rounded_value = round(value, 3)
        else:
            rounded_value = round(decimal.Decimal(value), 2)
        return str(rounded_value).replace(',', '.')
    return value


@register.filter(name='round_fourth')
def round_fourth(value):
    if value is not None and value != '':
        value = float(value)
        decimal_part = value - int(value)
        decimal_str = f"{decimal_part:.3f}"[2:]
        if int(decimal_str[2]) > 0:
            rounded_value = round(value, 4)
        else:
            rounded_value = round(decimal.Decimal(value), 4)
        return str(rounded_value).replace(',', '.')
    return value


@register.filter(name='replace_round_separator')
def replace_round_separator(value):
    if value is not None and value != '':
        value = float(value)
        decimal_part = value - int(value)
        decimal_str = f"{decimal_part:.3f}"[2:]
        if int(decimal_str[2]) > 0:
            rounded_value = round(value, 3)
        else:
            rounded_value = round(decimal.Decimal(value), 2)
        formatted_value = '{:,.{}f}'.format(rounded_value, 3 if int(decimal_str[2]) > 0 else 2).replace(',', 'X').replace('.', ',').replace('X', '.')
        return formatted_value
    return value


@register.filter(name='replace_round_separator_us')
def replace_round_separator_us(value):
    if value is not None and value != '':
        value = float(value)
        rounded_value = round(value, 2)
        formatted_value = '{:,.2f}'.format(rounded_value)
        return formatted_value
    return value


@register.filter
def divide_stock(stock, qm):
    try:
        new_stock = decimal.Decimal(stock) / decimal.Decimal(qm)
        return round(new_stock, 2)
    except (TypeError, ZeroDivisionError):
        return None

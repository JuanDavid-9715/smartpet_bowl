from django import template

register = template.Library()


@register.filter
def cop(value):
    try:
        number = int(value)
    except (TypeError, ValueError):
        return value
    return "COP " + f"{number:,.0f}".replace(",", ".")

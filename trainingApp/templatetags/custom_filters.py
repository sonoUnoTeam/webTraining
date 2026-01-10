# trainingApp/templatetags/custom_filters.py
from django import template
from django.utils.translation import gettext_lazy as _
register = template.Library()

#Metodo para obtener la clave de un diccionario
@register.filter
def get_value(dictionary, key):
    return dictionary.get(key, "0")
    
    
@register.filter
def get_state(dictionary, key):
    return dictionary[f'{key}']

@register.filter
def get_state_trans(dictionary, key):
    return _(dictionary[f'{key}'])

@register.filter
def subtract(value, arg):
    """Resta arg de value"""
    try:
        return int(value) - int(arg)
    except (ValueError, TypeError):
        return 0
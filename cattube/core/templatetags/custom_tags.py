from math import floor

from django import template
from django.urls import resolve

register = template.Library()


@register.filter
def hms(value):
    seconds = float(value)
    hours = floor(seconds / 3600)
    seconds -= hours * 3600
    minutes = floor(seconds / 60)
    seconds -= minutes * 60
    return f'{hours:02d}:{minutes:02d}:{seconds:05.2f}'

@register.filter
def join_by_key(the_list, key, separator=', '):
    return separator.join(obj[key] for obj in the_list)

@register.simple_tag
def is_url_name(request, url_name):
    try:
        return resolve(request.path_info).url_name == url_name
    except:  # noqa: E722
        return False

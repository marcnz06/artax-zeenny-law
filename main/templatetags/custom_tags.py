from django import template
from django.shortcuts import reverse
from django.utils.safestring import mark_safe

register = template.Library()


@register.simple_tag(takes_context=True)
def nav_link(context, view_name, text, icon, target=False, *args, **kwargs):
    current_view_name = context['request'].resolver_match.view_name
    if current_view_name.endswith(view_name):
        nav_class = 'nav-item'
        link_class = 'nav-link'
    else:
        nav_class = 'nav-item collapsed'
        link_class = 'nav-link collapsed'

    url = reverse(view_name, args=args, kwargs=kwargs)
    if target:
        return mark_safe(f"""<li class="{nav_class}"><a class="{link_class}" target="_blank" href="{url}"><i class="{icon}"></i><span>{text}</span></a></li>""")
    else:
        return mark_safe(f"""<li class="{nav_class}"><a class="{link_class}" href="{url}"><i class="{icon}"></i><span>{text}</span></a></li>""")

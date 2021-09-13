from django.template import Library
from django.conf import settings
from ..settings import configure_default_settings

configure_default_settings()

try:
    from urllib.parse import urlencode
except ImportError:
    from urllib import urlencode

import hashlib

register = Library()


def _gravatar(email, size=80, options=""):
    url = 'http'
    if settings.GRAVATAR_SECURE:
        url += 's'
    url += '://www.gravatar.com/avatar/' + hashlib.md5(email.lower().encode('utf-8')).hexdigest() + '?'
    url += urlencode([('s', str(size)), ('d', settings.GRAVATAR_DEFAULT_URL)])

    return url


@register.simple_tag
def gravatar(email, size=80, options=""):
    return '%s width="%s" height="%s" %s' % (_gravatar(email, size), size, size, options)


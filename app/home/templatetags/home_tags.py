import logging
from django import template
from django.conf import settings
from django.templatetags.static import static
from typing import Optional
from oauth.models import CustomUser

logger = logging.getLogger('app')
register = template.Library()


@register.simple_tag(name='get_config')
def get_config(value: str) -> Optional[str]:
    # get django setting value or return none
    return getattr(settings, value, None)


@register.filter(name='absolute_url')
def absolute_url(absolute_uri: str) -> str:
    # returns the absolute_url from the absolute_uri
    return '{0}//{2}'.format(*absolute_uri.split('/'))


@register.filter(name='avatar_url')
def avatar_url(user: CustomUser) -> str:
    # return discord avatar url from user model
    if user.avatar_hash:
        return f'https://cdn.discordapp.com/avatars/' \
               f'{ user.username }/{ user.avatar_hash }.png'
    else:
        return static('images/assets/default.png')

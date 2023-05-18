import httpx
import logging
import urllib.parse
from datetime import datetime, timedelta
from decouple import config, Csv
from django.contrib import messages
from django.contrib.auth import login, logout
from django.http import HttpRequest
from django.shortcuts import HttpResponseRedirect, redirect
from django.urls import reverse
from django.views.decorators.http import require_http_methods
from .models import CustomUser

logger = logging.getLogger('app')


def oauth_start(request):
    """
    View  /oauth/
    """
    request.session['login_redirect_url'] = get_next_url(request)
    params = {
        'redirect_uri': config('OAUTH_REDIRECT_URL'),
        'client_id': config('OAUTH_CLIENT_ID'),
        'response_type': config('OAUTH_RESPONSE_TYPE', 'code'),
        'scope': config('OAUTH_SCOPE', 'identify'),
        'prompt': config('OAUTH_PROMPT', 'none'),
    }
    url_params = urllib.parse.urlencode(params)
    url = f'https://discord.com/api/oauth2/authorize?{url_params}'
    return HttpResponseRedirect(url)


def oauth_callback(request):
    """
    View  /oauth/callback/
    """
    if 'code' not in request.GET:
        messages.warning(request, 'User aborted or no code in request.')
        return HttpResponseRedirect(get_login_redirect_url(request))

    try:
        logger.debug('code: %s', request.GET['code'])
        token_data = get_access_token(request.GET['code'])
        logger.debug('token_response: %s', token_data)
        profile = get_user_profile(token_data)
        logger.debug('profile: %s', profile)
        user, _ = CustomUser.objects.get_or_create(username=profile['id'])
        update_profile(user, profile)
        login(request, user)
        messages.info(request, f'Successfully logged in as {user.first_name}.')

    except Exception as error:
        logger.exception(error)
        messages.error(request, f'Exception during login: {error}')

    return HttpResponseRedirect(get_login_redirect_url(request))


@require_http_methods(['POST'])
def oauth_logout(request):
    """
    View  /oauth/logout/
    """
    next_url = get_next_url(request)

    # Hack to prevent login loop when logging out on a secure page
    if len(next_url.split('/')) > 1:
        logger.debug('next_url: %s', next_url.split('/')[1])
        secure_views_list = ['profile']
        if next_url.split('/')[1] in secure_views_list:
            next_url = '/'

    request.session['login_next_url'] = next_url
    logout(request)
    messages.info(request, f'Successfully logged out.')
    return redirect(next_url)


def get_access_token(code: str) -> dict:
    """
    Post OAuth code and Return access_token
    """
    url = 'https://discord.com/api/v8/oauth2/token'
    data = {
        'redirect_uri': config('OAUTH_REDIRECT_URL'),
        'client_id': config('OAUTH_CLIENT_ID'),
        'client_secret': config('OAUTH_CLIENT_SECRET'),
        'grant_type': config('OAUTH_GRANT_TYPE', 'authorization_code'),
        'code': code,
    }
    headers = {'Content-Type': 'application/x-www-form-urlencoded'}
    r = httpx.post(url, data=data, headers=headers, timeout=10)
    if not r.is_success:
        logger.info('status_code: %s', r.status_code)
        logger.error('content: %s', r.content)
        r.raise_for_status()
    return r.json()


def get_user_profile(token_data: dict) -> dict:
    """
    Get Profile for Authenticated User
    """
    url = 'https://discord.com/api/v8/users/@me'
    headers = {'Authorization': f"Bearer {token_data['access_token']}"}
    r = httpx.get(url, headers=headers, timeout=10)
    if not r.is_success:
        logger.info('status_code: %s', r.status_code)
        logger.error('content: %s', r.content)
        r.raise_for_status()
    logger.debug('r.json(): %s', r.json())
    p = r.json()
    # profile - Custom user data from oauth provider
    return {
        'id': p['id'],
        'username': p['username'],
        'discriminator': p['discriminator'],
        'avatar': p['avatar'],
        'access_token': token_data['access_token'],
        'refresh_token': token_data['refresh_token'],
        'expires_in': datetime.now() + timedelta(0, token_data['expires_in']),
    }


def update_profile(user: CustomUser, profile: dict) -> None:
    """
    Update Django user profile with provided data
    """
    user.first_name = profile['username']
    user.last_name = profile['discriminator']
    user.avatar_hash = profile['avatar']
    user.access_token = profile['access_token']
    user.refresh_token = profile['refresh_token']
    user.expires_in = profile['expires_in']
    if profile['id'] in config('SUPER_USERS', '', Csv()):
        logger.info('Super user login: %s', profile['id'])
        user.is_staff, user.is_admin, user.is_superuser = True, True, True
    user.save()


def get_next_url(request: HttpRequest) -> str:
    """
    Determine 'next' parameter
    """
    if 'next' in request.GET:
        return str(request.GET['next'])
    if 'next' in request.POST:
        return str(request.POST['next'])
    if 'next_url' in request.session:
        url = request.session['next_url']
        del request.session['next_url']
        request.session.modified = True
        return url
    return reverse('home:index')


def get_login_redirect_url(request: HttpRequest) -> str:
    """
    Determine 'login_redirect_url' parameter
    """
    if 'login_redirect_url' in request.session:
        url = request.session['login_redirect_url']
        del request.session['login_redirect_url']
        request.session.modified = True
        return url
    return reverse('home:index')

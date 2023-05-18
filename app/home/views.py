import httpx
import json
import logging
import time
from django.conf import settings
from django.core.cache import cache
from django.http import HttpRequest, JsonResponse
from django.shortcuts import render
from django.template.loader import render_to_string
from django.utils.crypto import get_random_string
from django_redis import get_redis_connection
from .forms import ContactForm
from .models import Contact

logger = logging.getLogger('app')


def home_view(request):
    # View: /
    logger.debug('home_view')
    logger.debug('is_secure: %s', request.is_secure())
    return render(request, 'home.html')


def contact_view(request):
    # View: /contact/
    logger.debug('contact_view')
    logger.debug('is_secure: %s', request.is_secure())
    if not request.method == 'POST':
        return render(request, 'contact.html')

    try:
        logger.debug(request.POST)
        form = ContactForm(request.POST)
        if not form.is_valid():
            logger.debug(form.errors)
            return JsonResponse(form.errors, status=400)

        if not request.user.is_authenticated and not google_verify(request):
            data = {'error_message': 'Google CAPTCHA not verified.'}
            return JsonResponse(data, status=400)

        contact = Contact.objects.create(
            name=form.cleaned_data['name'],
            message=form.cleaned_data['message'],
        )
        r = send_discord_message(contact.pk)
        if not r.is_success:
            logger.warning(r.content)
            r.raise_for_status()
        return JsonResponse({}, status=204)

    except Exception as error:
        logger.exception(error)
        return JsonResponse({'error_message': str(error)}, status=400)


def verify_view(request):
    # View: /verify/
    logger.debug('verify_view')
    logger.debug('is_secure: %s', request.is_secure())
    # logger.debug(request.META)

    if request.method == 'GET':
        logger.debug(request.GET)
        guild_id = request.GET.get('guild')
        logger.debug('guild_id: %s', guild_id)
        user_id = request.GET.get('user')
        logger.debug('user_id: %s', user_id)
        if not guild_id or not user_id:
            context = {'error': 'Invalid Request. No guild or user in query.'}
            return render(request, 'verify.html', context)

        br = cache.get(f'{guild_id}')
        if not br:
            br = bot_request('red.captcha', ['data'], guild_id, user_id)
            logger.debug('br: %s', br)
            if br:
                cache.set(f'{guild_id}', br, 30)
            else:
                context = {'error': 'Error fetching data from Discord.'}
                return render(request, 'verify.html', context)

        context = {'guild': br['guild'], 'member': br['member']}
        return render(request, 'verify.html', context)

    try:
        logger.debug(request.POST)
        if not google_verify(request):
            data = {'error_message': 'Google CAPTCHA not verified.'}
            return JsonResponse(data, status=400)

        guild = request.POST['guild']
        logger.debug('guild: %s', guild)
        user = request.POST['user']
        logger.debug('user: %s', user)
        data = {'guild': int(guild), 'user': int(user)}
        br = bot_request('red.captcha', ['verify'], guild, user, data)
        logger.debug('br: %s', br)
        if not br:
            context = {'error': 'Error fetching data from Discord.'}
            return render(request, 'verify.html', context)

        return JsonResponse({}, status=204)

    except Exception as error:
        logger.exception(error)
        return JsonResponse({'error_message': str(error)}, status=400)


def bot_request(channel: int | str,
                requests: list,
                guild_id: int | str,
                user_id: int | str = 0,
                data: dict = None) -> dict | None:
    try:
        # Send Data
        logger.debug('channel: %s', channel)
        return_channel = get_random_string(length=16)
        logger.debug('return_channel: %s', return_channel)
        r = get_redis_connection('default')
        p = r.pubsub(ignore_subscribe_messages=True)
        p.subscribe(return_channel)
        default = {
            'channel': return_channel,
            'guild': int(guild_id),
            'user': int(user_id),
            'requests': requests,
        }
        if data:
            logger.debug('data: %s', data)
            default.update(data)
        logger.debug('default: %s', default)
        pub_ret = r.publish(channel, json.dumps(default))
        logger.debug('pub_ret: %s', pub_ret)
        if pub_ret == 0:
            logger.warning('BOT NOT Listening on pubsub channel: %s', channel)
            return None

        # Get Data
        message = get_pubsub_message(p)
        return json.loads(message['data'].decode('utf-8'))

    except Exception as error:
        logger.warning('Error Getting BOT Data')
        logger.exception(error)
        return None


def google_verify(request: HttpRequest) -> bool:
    logger.debug('google_verify')
    if 'g_verified' in request.session and request.session['g_verified']:
        return True
    try:
        url = 'https://www.google.com/recaptcha/api/siteverify'
        data = {
            'secret': settings.GOOGLE_SITE_SECRET,
            'response': request.POST['g-recaptcha-response']
        }
        r = httpx.post(url, data=data, timeout=10)
        if r.is_success:
            if r.json()['success']:
                request.session['g_verified'] = True
                return True
        return False
    except Exception as error:
        logger.exception(error)
        return False


def send_discord_message(message: str) -> httpx.Response:
    logger.debug('send_discord_message')
    context = {'message': message}
    discord_message = render_to_string('message/discord-message.html', context)
    logger.debug('discord_message: %s', discord_message)
    data = {'content': discord_message}
    r = httpx.post(settings.DISCORD_WEBHOOK, json=data, timeout=5)
    logger.debug('r.status_code: %s', r.status_code)
    return r


def get_pubsub_message(pubsub, timeout: int = 6):
    logger.debug('get_pubsub_message')
    message = None
    now = time.time()
    t = now + timeout
    while now < t:
        message = pubsub.get_message(timeout=timeout)
        if message is not None:
            break
        time.sleep(0.01)
        now = time.time()
    return message

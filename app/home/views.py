import httpx
import json
import logging
import time
import redis
import xmltodict
from datetime import datetime
from django.conf import settings
from django.core.cache import cache
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import render
from django.template.loader import render_to_string
from django.utils.crypto import get_random_string
from django.views.decorators.csrf import csrf_exempt
from django_redis import get_redis_connection
from typing import Optional, Union, Any, Dict
from .forms import ContactForm
from .models import Contact

logger = logging.getLogger('app')


def home_view(request):
    # View: /
    logger.debug('home_view: is_secure: %s', request.is_secure())
    return render(request, 'home.html')


def contact_view(request):
    # View: /contact/
    logger.debug('contact_view: is_secure: %s', request.is_secure())
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


def fa_view(request):
    # View: /flightaware/
    logger.debug('fa_view: is_secure: %s', request.is_secure())
    if not request.method == 'GET':
        logger.debug('-'*20)
        logger.debug(request.GET)
    if not request.method == 'POST':
        logger.debug('-'*20)
        logger.debug(request.POST)

    # Form response
    r_title: str
    r_detail: str
    r_status: int
    data: Dict[str, Any] = request.json
    # Process data by getting things needed

    body = request.body.decode('utf-8')
    data: Dict[str, Any] = json.loads(body)
    logger.info(data)

    try:
        processed_data: Dict[str, Any] = {
            "long_description": data["long_description"],
            "short_description": data["short_description"],
            "summary": data["summary"],
            "event_code": data["event_code"],
            "alert_id": data["alert_id"],
            "fa_flight_id": data["flight"]["fa_flight_id"],
            "ident": data["flight"]["ident"],
            "registration": data["flight"]["registration"],
            "aircraft_type": data["flight"]["aircraft_type"],
            "origin": data["flight"]["origin"],
            "destination": data["flight"]["destination"],
        }

    except KeyError as error:
        logger.exception(error)
        return HttpResponse(status=400)
    except Exception as error:
        logger.exception(error)
        return HttpResponse(status=500)

    return HttpResponse()


@csrf_exempt
def plotly_view(request, pk: Optional[str] = None):
    # View: /plotly/
    logger.debug('%s - plotly_view - is_secure: %s', request.method, request.is_secure())
    try:
        if request.method == 'GET':
            logger.debug(request.GET)
            logger.debug(pk)
            data = cache.get(pk)
            logger.debug(data)
            if not data:
                return HttpResponse(status=404)
            return HttpResponse(data, status=200)

        if request.method == 'POST':
            logger.debug(request.POST)
            body = request.body.decode()
            logger.debug('-'*20)
            logger.debug(body)
            logger.debug('-'*20)
            key = str(datetime.now().timestamp())
            cache.set(key, body, 60*60*24*7)

    except Exception as error:
        logger.exception(error)
        return HttpResponse(status=400)


@csrf_exempt
def yt_view(request):
    # View: /youtube/
    logger.debug('%s - yt_view - is_secure: %s', request.method, request.is_secure())
    try:
        if request.method == 'GET':
            logger.debug(request.GET)
            challenge = request.GET.get('hub.challenge', None)
            logger.debug(challenge)
            if challenge:
                logger.debug('return 200: %s', challenge)
                return HttpResponse(challenge, status=200)
            logger.debug('return 400')
            return HttpResponse(status=400)

        if request.method == 'POST':
            logger.debug(request.POST)
            body = request.body.decode('utf-8')
            logger.debug('-'*20)
            logger.debug(body)
            logger.debug('-'*20)
            data = xmltodict.parse(body)
            logger.debug(data)
            r = bot_request('red.youtube', ['new'], 0, 0, data)
            logger.debug(r)
            logger.debug('return 204')
            return HttpResponse(status=204)

    except Exception as error:
        logger.exception(error)
        logger.debug('return 400')
        return HttpResponse(status=400)


def verify_view(request):
    # View: /verify/
    logger.debug('verify_view: is_secure: %s', request.is_secure())
    if request.method in ['GET', 'HEAD']:
        logger.debug(request.GET)
        guild_id = request.GET.get('guild')
        logger.debug('guild_id: %s', guild_id)
        user_id = request.GET.get('user')
        logger.debug('user_id: %s', user_id)
        # context = {'verified': False}
        if not guild_id or not user_id:
            context = {'error': 'Invalid Request. No guild or user in query.'}
            return render(request, 'verify.html', context)

        br = cache.get(f'br:{user_id}')
        if not br:
            br = bot_request('red.captcha', ['data'], guild_id, user_id)
            if br:
                cache.set(f'br:{user_id}', br, 15)
            else:
                context = {'error': 'Error fetching data from Discord.'}
                return render(request, 'verify.html', context)

        logger.debug('br: %s', br)
        context = {'guild': br['guild'], 'member': br['member']}
        if 'verified' in br and br['verified']:
            context['verified'] = True
        logger.debug('context: %s', context)
        return render(request, 'verify.html', context)

    try:
        logger.debug(request.POST)
        if not google_verify(request):
            context = {'error_message': 'Google CAPTCHA not verified.'}
            return JsonResponse(context, status=400)

        guild_id = request.POST['guild']
        logger.debug('guild: %s', guild_id)
        user_id = request.POST['user']
        logger.debug('user: %s', user_id)
        data = {'guild': int(guild_id), 'user': int(user_id)}
        br = bot_request('red.captcha', ['verify'], guild_id, user_id, data)
        logger.debug('br: %s', br)
        if not br:
            context = {'error_message': 'Error fetching data from Discord.'}
            return JsonResponse(context, status=400)

        if 'success' not in br or not br['success']:
            if 'message' in br:
                message = br['message']
            else:
                message = 'Error completing verification with Discord Bot.'
            return JsonResponse({'error_message': message}, status=400)

        cache.delete(f'br:{user_id}')
        # br = cache.get(f'br:{guild_id}')
        # if br:
        #     br.delete()
        return JsonResponse({}, status=204)

    except Exception as error:
        logger.exception(error)
        return JsonResponse({'error_message': str(error)}, status=400)


def bot_request(channel: Union[str, int], requests: list[str],
                guild_id: Union[str, int], user_id: Union[str, int],
                data: Optional[dict] = None) -> Optional[dict]:
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


def get_pubsub_message(pubsub: redis.client.PubSub,
                       timeout: int = 6) -> Optional[dict]:
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


def yt_sub(callback='https://intranet.cssnr.com/youtube/',
           channel_id='UCkHizGOU0va29RVjrfdz_Aw') -> int:
    data = {
        'hub.callback': callback,
        'hub.topic': f'https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}',
        'hub.verify': 'async',
        'hub.mode': 'subscribe',
        'hub.verify_token': '',
        'hub.secret': '',
        'hub.lease_numbers': '',
    }
    url = 'https://pubsubhubbub.appspot.com/subscribe'
    r = httpx.post(url, data=data, timeout=10)
    logger.debug('r.status_code: %s', r.status_code)
    if not r.is_success:
        r.raise_for_status()
    return r.status_code

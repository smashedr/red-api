import logging
from django.http import HttpResponse
from django.shortcuts import render

logger = logging.getLogger('app')


def health_check(request):
    return HttpResponse('success', status=200)


def handler400_view(request, exception):
    logger.debug('handler400_view')
    logger.debug(exception)
    return render(request, 'error/400.html', status=400)


def handler403_view(request, exception):
    logger.debug('handler403_view')
    logger.debug(exception)
    return render(request, 'error/403.html', status=403)


def handler404_view(request, exception):
    logger.debug('handler404_view')
    logger.debug(exception)
    return render(request, 'error/404.html', status=404)


def handler500_view(request):
    logger.debug('handler500_view')
    # logger.debug(exception)
    return render(request, 'error/500.html', status=500)

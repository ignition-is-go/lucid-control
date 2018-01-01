# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import logging
import json
import os

from django.shortcuts import render
from django.http.response import HttpResponse, HttpResponseBadRequest
from celery import Celery

from . import tasks
from .tasks import send_workday_checkin
from .models import Profile

def action_response(request):
    ''' handles all slack action message responses'''
    logger = logging.getLogger(__name__+": action_handler")
    # slack seems to send json all bundled in the 'payload' form var
    slack_data = json.loads(request.POST['payload'])
    if slack_data is None:
        # just in case slack changes
        slack_data = request.POST

    try:
        validate_slack(slack_data['token'])
    except InvalidSlackToken as e:
        return HttpResponse(e.message)
    else:
        # we've verified it's our slack app a-knockin'
        logger.info("Confirmed Slack token")

        if "challenge" in slack_data.keys():
            logger.info("Responding to challenge: %s", slack_data['challenge'])
            return slack_data['challenge']
        
        elif "callback_id" in slack_data.keys():
            # TODO: route what to do here
            logger.info("Routing callback: %s", slack_data['callback_id'])
            try:
                callback, question_id = str(slack_data['callback_id']).split("=", 1)
                func = getattr(tasks, callback)
                func(slack_data)
                return HttpResponse("")
            except ValueError:
                # bad callback, return 400
                return HttpResponseBadRequest()

def test(request, user):
    '''
    just for testing
    '''

    user = Profile.objects.get(user__username=user)
    send_workday_checkin(user.id)
    return HttpResponse("Testing!")

def validate_slack(token):
    if token != os.environ['LUCILLE_VERIFICATION_TOKEN']:
        # this token didn't come from slack
        raise InvalidSlackToken(
            'Invalid Slack Verification Token. Commands disabled '
            'until token is corrected. Try setting the '
            'SLACK_VERIFICATION_TOKEN environment variable.'
        )
    else:
        return True

class InvalidSlackToken(Exception):
    pass
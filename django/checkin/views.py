# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import logging
import json
import os

import arrow
import slacker

from django.shortcuts import render
from django.http.response import HttpResponse, HttpResponseBadRequest, JsonResponse
from celery import Celery

from . import tasks
from .tasks import send_workday_checkin
from .models import Profile, Workday

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
                func.delay(slack_data)
                return HttpResponse("")
            
            except ValueError:
                # bad callback, return 400
                return HttpResponseBadRequest()

def roll_call(request):
    '''
    does a roll call of today's checkins
    '''

    try:
        validate_slack(request.POST['token'])
    except InvalidSlackToken as e:
        return HttpResponse(e.message)
    else:
        # verified it's slack!
        # for getting local timezone, for now defaulting to PT
        # slack = slacker.Slacker(os.environ.get("SLACK_APP_TEAM_TOKEN"))
        # user_data = slack.users.info(user.slack_user)
        # tz = user_data.body['user']['tz']
        today = Workday.objects.filter(date=arrow.now('America/Los_Angeles').date())
        
        fields = []
        fallback = ""
        for checkin in today:
            name = checkin.user.user.get_full_name() or checkin.user.user.__str__()
            status = checkin.current_status.__str__()
            fields.append(
                {
                    'title': name,
                    'value': status,
                    'short': True
                }
            )
            fallback="|{}:{}\r".format(name, status)

        message = dict(
            text = "",
            attachments = [dict(
                fallback=fallback,
                fields=fields
            )],
            response_type="ephemeral",
            parse=True,
            as_user=True
        )

        return JsonResponse(message)
        # slack = slacker.Slacker(os.environ.get("LUCILLE_BOT_TOKEN"))
        
        # slack.chat.post_message(
        #     channel=request.POST['channel_id'],
        #     text=None,
        #     as_user=True,
        #     attachments=[dict(
        #         fallback=fallback,
        #         fields=fields
        #     )],
        # )

def set_timezone(request):
    '''
    does a roll call of today's checkins
    '''

    try:
        validate_slack(request.POST['token'])
    except InvalidSlackToken as e:
        return HttpResponse(e.message)
    else:
        # verified it's slack!
        # for getting local timezone, for now defaulting to PT
        # slack = slacker.Slacker(os.environ.get("SLACK_APP_TEAM_TOKEN"))
        # user_data = slack.users.info(user.slack_user)
        # tz = user_data.body['user']['tz']
        today = Workday.objects.filter(date=arrow.now('America/Los_Angeles').date())
        
        fields = []
        fallback = ""
        for checkin in today:
            name = checkin.user.user.get_full_name() or checkin.user.user.__str__()
            status = checkin.current_status.__str__()
            fields.append(
                {
                    'title': name,
                    'value': status,
                    'short': True
                }
            )
            fallback="|{}:{}\r".format(name, status)

        message = dict(
            text = "",
            attachments = [dict(
                fallback=fallback,
                fields=fields
            )],
            response_type="ephemeral",
            parse=True,
            as_user=True
        )

        return JsonResponse(message)
        

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
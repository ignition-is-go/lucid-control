# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import logging
import requests
import simplejson as json

from django.shortcuts import render
from django.http import JsonResponse, HttpResponse
from .slack_handler import send_confirmation, check_confirmation

def slash_command(request, command):
    ''' handles the initial slash commands and sends a confirmation'''
    try:
        validate_slack(request.POST['token'])
    except InvalidSlackToken as e:
        return HttpResponse(e.message)
    else:
        # we've validated the command came from our slack
        send_confirmation(request.POST)
    pass

def action_response(request):
    ''' handles all slack action message responses'''
    logger = logging.getLogger(__name__+": action_handler")
    # slack tends to send json all bundled in the 'payload' form var
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
            channel_id, command, arg = check_confirmation(slack_data)

            # send to celery task




def validate_slack(token):
    if token != os.environ['SLACK_VERIFICATION_TOKEN']:
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
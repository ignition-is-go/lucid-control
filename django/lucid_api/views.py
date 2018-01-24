# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import logging
import os
import simplejson as json

from django.http import Http404
from django.http.response import JsonResponse, HttpResponse
from rest_framework import generics, permissions
from rest_framework.views import APIView
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.reverse import reverse_lazy
from .models import Project
from .serializers import ProjectSerializer
from .handlers.slack_handler import send_confirmation, check_confirmation
from .tasks import execute_slash_command

######################
# REST API
######################

@api_view(['GET'])
@permission_classes((permissions.IsAuthenticated,))
def api_root(request, format=None):
    '''
    Root of the API for docs
    '''

    return Response({
        'projects': reverse_lazy('api:project_list', request=request, format=format),
    })

class ProjectList(generics.ListCreateAPIView):
    queryset = Project.objects.all()
    serializer_class = ProjectSerializer
    permission_classes = (permissions.DjangoModelPermissions,)

class ProjectDetail(generics.RetrieveUpdateDestroyAPIView):
    queryset = Project.objects.all()
    serializer_class = ProjectSerializer
    permission_classes = (permissions.DjangoModelPermissions,)


###########################
# handling slack commands 
###########################

def slash_command(request, command):
    ''' handles the initial slash commands and sends a confirmation'''
    try:
        validate_slack(request.POST['token'])
    except InvalidSlackToken as e:
        return HttpResponse(e.message)
    else:
        # we've validated the command came from our slack
        send_confirmation(request.POST, command)
        return HttpResponse("")
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
            try:
                channel_id, command, arg = check_confirmation(slack_data)
                # send to celery task
                execute_slash_command.delay(command, arg, channel_id)

            except:
                pass

            return HttpResponse("")


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
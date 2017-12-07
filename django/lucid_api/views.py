# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import logging

from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response
from .models import Project
from .serializers import ProjectSerializer
from .handlers.slack_handler import send_confirmation, check_confirmation
# from .tasks import create, rename, archive


@api_view(['GET', 'POST'])
def project_list(request, format=None):
    """
    List all projects, or create a new project.
    """
    if request.method == 'GET':
        snippets = Project.objects.all()
        serializer = ProjectSerializer(snippets, many=True)
        return Response(serializer.data)

    elif request.method == 'POST':
        serializer = ProjectSerializer(data=request.data)
        if serializer.is_valid():
            project = serializer.save()
            # kick off celery task here
            # TODO: does this work? 
            # create.delay(project.title)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['GET', 'PUT', 'DELETE'])
def project_detail(request, pk, format=None):
    """
    Retrieve, update or delete a  project.
    """
    try:
        project = Project.objects.get(pk=pk)
    except Project.DoesNotExist:
        return Response(status=status.HTTP_404_NOT_FOUND)

    if request.method == 'GET':
        serializer = ProjectSerializer(project)
        return Response(serializer.data)

    elif request.method == 'PUT':
        serializer = SnippetSerializer(project, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    elif request.method == 'DELETE':
        project.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


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
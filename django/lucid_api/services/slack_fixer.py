import logging
import os

import slacker
import slack_service
from django.apps import apps


def get_unhinged_slack_connections():
    '''
    gets the slack connections from db that have no identifier and no name
    '''
    logger = logging.getLogger(__name__)

    ServiceConnection = apps.get_model("lucid_api", "ServiceConnection")
    connections = ServiceConnection.objects.filter(service_name="slack_service", identifier="")

    logger.info("found %d slack connections to fix", len(connections))

    return connections


def find_channel(slack, slug):
    '''
    Finds and returns a slack channel dictionary for the given project number
    '''
    logger = logging.getLogger(__name__)
    logger.info('Searching for channel for #%s',slug)

    # might need to page?
    channels = slack.channels.list(exclude_archived=True,exclude_members=True)

    logger.debug("Stepping through existing channels")
    for channel in channels.body['channels']:
        logger.debug("Checking channel %s", channel['name'])
        if slug.startswith( channel['name'] ):
            logger.info('Found channel for #%s: %s',slug,channel)
            return channel
    
    raise AttributeError("Couldn't find slack channel for project # %s", slug)


def do_it(test=True):
    '''
    does the fix
    '''
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)
    connections = get_unhinged_slack_connections()

    slack = slack_service.Service()

    for connection in connections:
        slug = slack._format_slug(connection).lower()
        logger.info("Slug for %s is %s", connection, slug)

        try:
            channel = find_channel(slack._slack_team, slug)
        except:
            logger.error("Couldn't match %s", slug, exc_info=True)
        else:
            logger.info("MATCHED! ::  %s is %s", channel['id'], slug)

            if not test:
                connection.identifier = channel['id']
                connection.save()
    


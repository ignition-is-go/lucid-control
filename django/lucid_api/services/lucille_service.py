'''
Service template
extend this to create a service for Lucid Control

K Bjordahl
6/20/17
'''

import service_template
import re
import os
import sys
import json
import logging

from django.conf import settings
from graphqlclient import GraphQLClient

from django.apps import apps
from celery.utils.log import get_task_logger


class Service(service_template.ServiceTemplate):

    _DEFAULT_REGEX = re.compile(
        r'^(?P<typecode>[A-Z])-(?P<project_id>\d{4})-(?P<project_title>.+)')
    _DEFAULT_FORMAT = "{typecode}-{project_id:04d}-{title}"
    _pretty_name = "Lucille Service"

    _upsert_mutation = '''
    mutation {{
        upsertProject(
            lucidId: {p.id}
            name: "{p.title}"
            typeCode: "{p.type_code.chr}"
        )
        {{
            id
            slug
        }}
    }}
    '''

    _archive_mutation = '''
    mutation {{
        archiveProject(
            lucidId: {p.id}
        ){{
            id
            openForTimeLogging
        }}
    }}
    '''

    _unarchive_mutation = '''
    mutation {{
        unarchiveProject(
            lucidId: {p.id}
        ){{
            id
            openForTimeLogging
        }}
    }}
    '''

    def __init__(self):
        '''
        create graphql client
        '''
        self._logger = get_task_logger(__name__)

        self._client = GraphQLClient(os.environ.get('LUCILLE_ADDRESS'))
        self._client.inject_token(os.environ.get('LUCILLE_TOKEN'))

        self._logger.info('Instantiated Lucille Service')

    def create(self, service_connection_id):
        '''
        Creates project using gql on lucille
        '''
        self._logger.debug('getting ServiceConnection id=%s',
                           service_connection_id)
        ServiceConnection = apps.get_model("lucid_api", "ServiceConnection")
        connection = ServiceConnection.objects.get(pk=service_connection_id)
        project = connection.project
        self._logger.info('creating lucille project for %s - %s',
                          project.id, project.title)
        try:
            # send the upsert mutation, with variables subbed in
            self._logger.debug('preparing mutation:\n%s',
                               self._upsert_mutation.format(p=project))
            result = self._client.execute(
                self._upsert_mutation.format(p=project))

            # parse the result as json
            data = json.loads(result)['data']['upsertProject']
            self._logger.debug('received result from lucille: %s', data)
            connection.identifier = data['id']
            connection.state_message = "Success: Lucille project id: {}".format(
                data['id'])
            connection.save()
            self._logger.info(
                'Successfully created project %s-%s in lucille (id:%s)', project.id, project.title, data['id'])
        except Exception as e:
            self._logger.error(
                'Error creating project in Lucille: %s', e, exc_info=True)
            raise e

    def rename(self, service_connection_id):
        '''
        same as create
        '''

        self.create(service_connection_id)

    def archive(self, service_connection_id):
        ServiceConnection = apps.get_model("lucid_api", "ServiceConnection")
        connection = ServiceConnection.objects.get(pk=service_connection_id)
        project = connection.project
        try:
            self._logger.debug('preparing mutation:\n%s',
                               self._archive_mutation.format(p=project))

            result = self._client.execute(
                self._archive_mutation.format(p=project))

            data = json.loads(result)['data']['archiveProject']

            if not data['openForTimeLogging']:
                connection.state_message = "Success: time logging disabled on Lucille project id: {}".format(
                    data['id'])
                connection.save()
            else:
                connection.state_message = "FAILED: {}".format(
                    data)
                connection.save()
                raise LucilleException('Project did not disable time logging')
            self._logger.info(
                'Successfully created project %s-%s in lucille (id:%s)', project.id, project.title, data['id'])
        except Exception as e:
            self._logger.error(
                'Error creating project in Lucille: %s', e, exc_info=True)
            raise e

    def unarchive(self, service_connection_id):
        ServiceConnection = apps.get_model("lucid_api", "ServiceConnection")
        connection = ServiceConnection.objects.get(pk=service_connection_id)
        project = connection.project
        try:
            self._logger.debug('preparing mutation:\n%s',
                               self._unarchive_mutation.format(p=project))

            result = self._client.execute(
                self._unarchive_mutation.format(p=project))

            data = json.loads(result)['data']['unarchiveProject']

            if data['openForTimeLogging']:
                connection.state_message = "Success: Now able to log time on Lucille project id: {}".format(
                    data['id'])
                connection.save()
            else:
                connection.state_message = "FAILED: {}".format(
                    data)
                connection.save()
                raise LucilleException('Project did not enable time logging')
            self._logger.info(
                'Successfully created project %s-%s in lucille (id:%s)', project.id, project.title, data['id'])
        except Exception as e:
            self._logger.error(
                'Error creating project in Lucille: %s', e, exc_info=True)
            raise e


class LucilleException(service_template.ServiceException):
    pass

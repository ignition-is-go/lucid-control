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
import logging

from django.conf import settings
from graphqlclient import GraphQLClient


class Service(service_template.ServiceTemplate):

    _DEFAULT_REGEX = re.compile(
        r'^(?P<typecode>[A-Z])-(?P<project_id>\d{4})-(?P<project_title>.+)')
    _DEFAULT_FORMAT = "{typecode}-{project_id:04d}-{title}"
    _pretty_name = "Lucille Service"

    _upsert_mutation = '''
	mutation {
		upsertProject(
			where: {
				lucidId: {p.id}
			}
			create: {
				lucidId: {p.id}
				name: {p.title}
				typeCode: {p.type_code}
			}
			update: {
				name: {p.title}
				typeCode: {p.type_code}
			}
		){
			id
			slug
		}
	}
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
        ServiceConnection = apps.get_model("lucid_api", "ServiceConnection")
        connection = ServiceConnection.objects.get(pk=service_connection_id)
        project = connection.project
        try:
            result = self._client.execute(
                self._upsert_mutation.format(p=project))

            connection.identifier = result.id
            connection.state_message = "Success: Lucille project id: {}".format(
                result.id)
            connection.save()
            self._logger.info(
                'Successfully created project %s-%s in lucille (id:%s)', project.id, project.title, result.id)
        except e as Exception:
            self._logger.error(
                'Error creating project in Lucille: %s', e, exc_info=True)
            raise e

	def rename(self, service_connection_id):
		'''
		same as create
		'''

		self.create(service_connection_id)

	def archive(self, service_connection_id):
		pass

	def unarchive(self, service_connection_id):
		pass
		

    def _setup_logger(self, level=settings.LOG_LEVEL_TYPE, to_file=True):
        '''
        DEPRECIATED AFTER MOVE TO DJANGO/CELERY
        Sets up the logger for the service

        Args:
                level (str): logging level as a string "info", "debug", "warn", "error", "critical"
        '''

        logger = logging.getLogger(type(self).__name__)
        assert isinstance(logger, logging.Logger)

        try:
            logging_path = os.environ['LOG_PATH']
        except KeyError:
            logging_path = "/logs"

        if to_file and not settings.IS_HEROKU:
            if not os.path.isdir(logging_path):
                os.mkdir(logging_path)
            log_path = os.path.join(
                logging_path, '{}.log'.format(type(self).__name__))
            handler = logging.FileHandler(log_path)
            formatter = logging.Formatter(
                '%(asctime)s | %(levelname)-7s| %(module)s.%(funcName)s :: %(message)s')
            handler.setFormatter(formatter)
            logger.addHandler(handler)

        elif settings.IS_HEROKU:
            handler = logging.StreamHandler(sys.stdout)
            formatter = logging.Formatter(
                '%(levelname)-7s| %(module)s.%(funcName)s :: %(message)s')
            handler.setFormatter(formatter)
            logger.addHandler(handler)

        return logger

    def get_pretty_name(self):
        return self._pretty_name

    def get_link(self, project_id):
        return ""

    def get_link_dict(self, project_id):
        return {self.get_pretty_name(): self.get_link(project_id)}

    def _format_slug(self, connection):
        '''
        Formats the slug based on the connection data.

        # Args:
        - **connection**: a *connection* model object from lucid-api
        '''

        return self._DEFAULT_FORMAT.format(
            typecode=connection.project.type_code.character_code,
            project_id=connection.project.id,
            title=connection.project.title,
            connection_name=connection.connection_name
        )


class ServiceException(Exception):
    pass

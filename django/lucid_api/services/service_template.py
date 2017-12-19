'''
Service template
extend this to create a service for Lucid Control

K Bjordahl
6/20/17
'''

import re
import os
import sys
import logging

from django.conf import settings


class ServiceTemplate(object):

    _DEFAULT_REGEX = re.compile(r'^(?P<typecode>[A-Z])-(?P<project_id>\d{4})-(?P<project_title>.+)')
    _DEFAULT_FORMAT = "{typecode}-{project_id:04d}-{title}"
    _pretty_name = "Generic Service"
    

    def _setup_logger(self, level=settings.LOG_LEVEL_TYPE, to_file=True):
        '''
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
            if not os.path.isdir(logging_path): os.mkdir(logging_path)
            log_path = os.path.join(logging_path, '{}.log'.format(type(self).__name__))
            handler = logging.FileHandler(log_path)
            formatter = logging.Formatter('%(asctime)s | %(levelname)-7s| %(module)s.%(funcName)s :: %(message)s')
            handler.setFormatter(formatter)
            logger.addHandler(handler)  

        elif settings.IS_HEROKU:
            handler = logging.StreamHandler(sys.stdout)
            formatter = logging.Formatter('%(levelname)-7s| %(module)s.%(funcName)s :: %(message)s')
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

        ### Args:
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
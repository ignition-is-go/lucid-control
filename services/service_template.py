'''
Service template
extend this to create a service for Lucid Control

K Bjordahl
6/20/17
'''

import re
import os
import logging
import constants

class ServiceTemplate(object):

    _DEFAULT_REGEX = re.compile(r'^(?P<typecode>[A-Z])-(?P<project_id>\d{4})-(?P<project_title>.+)')
    _DEFAULT_FORMAT = "{typecode}-{project_id:04d}-{title}"
    _pretty_name = "Generic Service"

    def _setup_logger(self, level=constants.LOG_LEVEL, to_file=False):
        '''
        Sets up the logger for the service

        Args:
            level (str): logging level as a string "info", "debug", "warn", "error", "critical"
        '''
        
        logger = logging.getLogger(type(self).__name__)

        if level.lower()[0] == 'w': logger.setLevel(logging.WARN)
        if level.lower()[0] == 'e': logger.setLevel(logging.ERROR)
        if level.lower()[0] == 'i': logger.setLevel(logging.INFO)
        if level.lower()[0] == 'd': logger.setLevel(logging.DEBUG)
        if level.lower()[0] == 'c': logger.setLevel(logging.CRITICAL)

        if to_file:
            handler = logging.FileHandler('{}.log'.format(type(self).__name__))
            formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
            handler.setFormatter(formatter)
            logger.addHandler(handler)        

        return logger

    def get_pretty_name(self):
        return self._pretty_name

    def get_link(self, project_id):
        return "_No Link Defined_"
        
    def _format_slug(self, project_id, title):
        m = re.match(self._DEFAULT_REGEX, title)

        if m is not None:
            # this means we've matched the regex
            if int(m.group('project_id')) == project_id:
                # confirm the project id's match, so extract just the title
                title = m.group('project_title')
                typecode = m.group('typecode')
        else:
            typecode = "P"

        return self._DEFAULT_FORMAT.format(
            typecode=typecode,
            project_id=project_id,
            title=title
            )

class ServiceException(Exception):
    pass
'''
Service template
extend this to create a service for Lucid Control

K Bjordahl
6/20/17
'''

import re

class ServiceTemplate(object):

    _DEFAULT_REGEX = re.compile(r'^P-(?P<project_id>\d{4})-(?P<project_title>.+)')
    _DEFAULT_FORMAT = "P-{project_id:04d}-{title}"

    @classmethod
    def _format_slug(cls, project_id, title):
        return cls._DEFAULT_FORMAT.format(
            project_id=project_id,
            title=title
            )
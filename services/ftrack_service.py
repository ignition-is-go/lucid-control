'''
ftrack service

for Lucid Control

K Bjordahl
6/19/2017


Implements access to ftrack in Lucid Control
'''

import ftrack_api
import os 
import logging
import re
from types import *
import service_template

class FtrackService(service_template.ServiceTemplate):

    _server = None
    _connected = None

    _pretty_name = "ftrack"

    def __init__(self, server_url=None, api_key=None, api_user=None, slug_regex=None):
        '''
        Constructor:
        @param server_url: ftrack server URL (must be HTTPS)
        @param api_key: ftrack api key
        @param api_user: ftrack api user name 

        creates an API connection and connects to the server
        '''
        
        self._logger = self._setup_logger(level='info',to_file=True)

        try:
            if server_url is None:
                server_url = os.environ.get('FTRACK_SERVER')
            
            if api_key is None:
                api_key = os.environ.get('FTRACK_API_KEY')

            if api_user is None:
                api_user = os.environ.get('FTRACK_API_USER')

            if slug_regex is not None:
                self._DEFAULT_REGEX = slug_regex

            self._server = ftrack_api.Session(
                server_url=server_url,
                api_key=api_key,
                api_user=api_user
                )
            self._logger.info('Initializing FTrack Server as: %s with API user %s', server_url, api_user)
        except TypeError as e:
            self._logger.error("Seems that some environment variables may be missing")
            raise e

    def is_connected(self):
        '''
        returns connection state for testing
        '''

        test = bool(len(self._server.types.keys()))

        self._connected = test

        return self._connected


    def create(self, project_id, title, silent=None):
        '''
        creates a new ftrack project
        '''
        default_schema_name = os.environ.get("FTRACK_DEFAULT_SCHEMA_NAME")
        assert default_schema_name is not None, "Please set env var 'FTRACK_DEFAULT_SCHEMA_NAME'"

        slug = self._format_slug(project_id,title)

        self._logger.info('Start create project for %s', slug)

        lucid_schema = self._server.query(
            'ProjectSchema where name is "{}"'.format(default_schema_name)).one()

        project = self._server.create('Project', {
            'name': project_id,
            'full_name': slug,
            'project_schema': lucid_schema
        })
        self._logger.debug('Created project %s (ID: %s)', slug, project_id)

        # add default components:
        # TODO: Add default items with task templates

        sale = self._server.create('Sale', {
            'name': 'Sale',
            'parent': project
        })
        self._logger.debug('Created sales item in %s', project['full_name'])

        project_management = self._server.create('ProjectManagement', {
            'name': 'Management',
            'parent': project
        })
        self._logger.debug('Created project management item in %s', project['full_name'])

        schedule = self._server.create('Schedule', {
            'name': 'Schedule',
            'parent': project
        })
        self._logger.debug('Created schedule item in %s', project['full_name'])

        self._server.commit()

        # do a query check
        check_project = self._find(project_id)
        return bool(check_project['full_name'] == slug)


    def rename(self, project_id, new_title):
        '''
        Rename an ftrack project
        Args:
            project_id (int): the project id number to search for
            new_title (str): the new title for the project including any P-####

        @return success boolean
        '''
        new_slug = self._format_slug(project_id,new_title)

        self._logger.info('Start project rename - change %s to %s', project['full_name'], new_slug)

        try:
            project = self._find(project_id)
        
        except FtrackServiceError:
            self._logger.debug('Unable to rename project %s as it already exists!', project['full_name'])
            return False
        
        else:
            old_slug = project['full_name']
            project['full_name'] = new_slug
            self._server.commit()
            self._logger.debug('Renamed project %s to %s', old_slug, project['full_name'])

            # do a query check
            check_project = self._find(project_id)
            return bool(check_project['full_name'] == new_slug)

    def archive(self, project_id, unarchive=False):
        '''
        Archive an ftrack project

        Args:
            project_id (int): the project id to archive
        
        Returns:
            bool: Success or not
        '''
        try:
            project = self._find(project_id)
        
        except FtrackServiceError:
            return False
        
        else:
            if unarchive:
                new_status = "active"
            else:
                # hidden is the ftrack version of archived
                new_status = "hidden"

            project['status'] = new_status
            self._server.commit()

            # do a query check
            check_project = self._find(project_id)
            return bool(check_project['status'] == new_status)

        
    def get_link(self, project_id):
        '''
        Generates a deep-link into the ftrack client for the project
        
        Args:
            project_id (int): the project_id number to get a link for

        Returns:
            str: URL for the project
        '''
        try:
            project = self._find(project_id)
        
        except FtrackServiceError:
            return False
        
        else:
            url = "{server}/#entityType=show&entityId={project[id]}\
&itemId=projects&view=tasks".format(
                project=project,
                server=self._server.server_url
            )

            return url

    def _find(self, project_id):
        '''
        finds an ftrack project by project_id
        '''
        self._logger.info("Trying to find Project ID # %s", project_id)

        projects = self._server.query('Project where name is "{}"'.format(project_id))

        if len(projects) > 1:
            self._logger.debug("Got more than one hit on the project number=%s", project_id)
            for project in projects:
                self._logger.debug("Project#: %s\t Title: %s",
                                   project['name'],
                                   project['full_name']
                                  )

                # we return the first project who's full name has the project code
                m = re.match(self._DEFAULT_REGEX, project['full_name'])
                if m.group('project_id') is not None:
                    self._logger.debug("%s has a project code", project['full_name'])
                    test_number = int(m.group('project_id'))
                    if test_number == int(project_id):
                        return project
            
            # We didn't settle on a regex match, so now we give up            
            raise FtrackServiceError("Found too many Project ID # {} \
                                      and couldn't decide which to use"
                                     .format(project_id))
        else:
            return projects[0]


class FtrackServiceError(service_template.ServiceException):
    pass

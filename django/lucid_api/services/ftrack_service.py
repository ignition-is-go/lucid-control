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
        
        self._logger = self._setup_logger(to_file=True)

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
            self._logger.info('Initializing %s with API user %s', server_url, api_user)
        except TypeError as e:
            self._logger.error("Environment variables may be missing")
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

        self._logger.info('Project: %s', slug)

        try:
            self._find(project_id)
        except FtrackServiceError:
            #this means that _find failed to find an existing project! carry on...
                
            lucid_schema = self._server.query(
                'ProjectSchema where name is "{}"'.format(default_schema_name)).one()

            project = self._server.create('Project', {
                'name': project_id,
                'full_name': slug,
                'project_schema': lucid_schema
            })
            self._logger.debug('Project: %s (ID: %s)', slug, project_id)

            # add default components:
            # TODO: Add default items from sample project

            # sale = self._server.create('Sale', {
            #     'name': 'Sale',
            #     'parent': project
            # })
            # self._logger.debug('Created sales item in %s', project['full_name'])

            # project_management = self._server.create('ProjectManagement', {
            #     'name': 'Management',
            #     'parent': project
            # })
            # self._logger.debug('Created project management item in %s', project['full_name'])

            # schedule = self._server.create('Schedule', {
            #     'name': 'Schedule',
            #     'parent': project
            # })
            # self._logger.debug('Created schedule item in %s', project['full_name'])

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

        self._logger.info('Changing project %s to %s', project_id, new_slug)

        try:
            project = self._find(project_id)
        
        except FtrackServiceError:
            self._logger.debug('Project %s already exists!', project['full_name'])
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

        self._logger.info('Starting for %s', project_id)

        try:
            project = self._find(project_id)
        
        except FtrackServiceError:
            self._logger.debug('Unable to find project %s to archive.', project_id)
            return False
        
        else:
            if unarchive:
                new_status = "active"
                self._logger.debug('Unarchive flag set for project %s', project_id)
            else:
                # hidden is the ftrack version of archived
                new_status = "hidden"
                self._logger.debug('Archive flag set for project %s', project_id)

            project['status'] = new_status
            self._server.commit()
            self._logger.debug('Status for project %s has been set to %s.', project_id, project['status'])

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
        
        self._logger.info('Start for %s', project_id)

        try:
            project = self._find(project_id)
        
        except FtrackServiceError:
            self._logger.debug('Unable to find project %s to create link.', project_id)
            return False
        
        else:
            url = "{server}/#entityType=show&entityId={project[id]}&itemId=projects&view=tasks".format(
                project=project,
                server=self._server.server_url
            )
            self._logger.debug('Link created for project %s: %s ', project_id, url)
            return url


    def get_link_dict(self, project_id):
        '''gets a link dictionary with a link name for display'''

        return {":lucid-control-ftrack: " + self.get_pretty_name() : self.get_link(project_id)}

    def _find(self, project_id):
        '''
        finds an ftrack project by project_id
        '''
        self._logger.info("Finding Project ID # %s", project_id)

        projects = self._server.query('Project where name is "{}"'.format(project_id))

        if len(projects) > 1:
            self._logger.debug("Found multiple projects with Project ID%s", project_id)
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
        elif len(projects) == 1:
            self._logger.debug('Found project ID # %s', project_id)
            return projects[0]
        else:
            self._logger.debug("Did not find project ID # %s",project_id)
            raise FtrackServiceError("Couldn't find a match for {}".format(project_id))


    def create_lead(self, lead_text, user_email):
        '''Creates a lead task in the Leads ftrack project as designated by the env var 'FTRACK_LEAD_PROJECT' '''
        self._logger.info("Attempting to create lead %s by user %s", lead_text, user_email)
        user_ftrack = ftrack_api.Session(api_user=user_email)
        lead_project_name = os.environ['FTRACK_LEAD_PROJECT']
        try:
            lead_project = user_ftrack.query("Project where (name like '{name}' or full_name like '{name}')".format(name=lead_project_name)).one()
            self._logger.debug("Found Lead project, name=%s", lead_project['name'])
            task = {
                'name': lead_text,
                'parent': lead_project,
                }
        except ftrack_api.exception.NotFoundError as err:
            self._logger.error("Couldn't find project named %s (%s)", lead_project_name, err.message)
            raise FtrackServiceError("Couldn't find ftrack project {}. _Check Env variables...({})_".format(lead_project_name, err.message))
        
        try:
            task['type'] = user_ftrack.query("Type where name like '%Slack'").one()
            self._logger.debug("Found Slack task type %s", task['type']['name'])
        except: 
            self._logger.warn("Couldn't find Slack task type, going with Generic")
            task['type'] = user_ftrack.query("Type where name like '%Generic%'").one()
                
        self._logger.debug("Running ftrack.create for %s",task)
        lead_task = user_ftrack.create("Task", task)

        try:
            user = user_ftrack.query("User where email is '{}'".format(user_email)).one()
            self._logger.debug("Found User %s:%s",user['first_name'], user['email'])
        except:
            self._logger.error("Couldn't find user for email %s", user_email)
            raise FtrackServiceError("Could not find user with email {}".format(user_email))
        else:
            self._logger.debug("Creating assignment of %s to task %s", user['email'], lead_task['name'])
            try:
                appt = user_ftrack.create("Appointment", {
                    'context': lead_task,
                    'resource': user,
                    'type': 'assignment'
                })

            except Exception as err:
                self._logger.error("Error while assigning task: %s", err.message )
                raise FtrackServiceError("Ran into a problem assigning the lead task._ftrack error: {}_".format(err.message))

        finally:
            self._logger.debug("Committing changes to ftrack server")
            try:
                # save changes to ftrack server
                user_ftrack.commit()
                self._logger.info("Finished creating lead %s", lead_text)

                # make a link for the new lead
                url = "{base}#slideEntityId={task_id}&slideEntityType=task&view=tasks&itemId=projects&entityId={project_id}&entityType=show".format(
                    task_id=lead_task['id'], project_id=lead_project['id'], base=os.environ['FTRACK_SERVER']
                )
                self._logger.debug("Url=[%s]", url)
                return url

            except Exception as err:
                self._logger.error("Error while committing changes: %s", err.message )
                raise FtrackServiceError("Ran into a problem._ftrack error: {}_".format(err.message))
            


class FtrackServiceError(service_template.ServiceException):
    pass

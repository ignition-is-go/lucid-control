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

from django.apps import apps
from celery.utils.log import get_task_logger

class Service(service_template.ServiceTemplate):

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
        
        self._logger = get_task_logger(__name__)

        try:
            if server_url is None:
                server_url = os.environ.get('FTRACK_SERVER')
                self._logger.debug("Server url is %s", server_url)
            
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


    def create(self, service_connection_id):
        '''
        creates a new ftrack project
        '''
        default_schema_name = os.environ.get("FTRACK_DEFAULT_SCHEMA_NAME")
        assert default_schema_name is not None, "Please set env var 'FTRACK_DEFAULT_SCHEMA_NAME'"

        ServiceConnection = apps.get_model("lucid_api", "ServiceConnection")
        connection = ServiceConnection.objects.get(pk=service_connection_id)
        project = connection.project

        self._logger.info(
            'Start Create ftrack for %s: %s',
            connection,
            project.title
            )

        slug = self._format_slug(connection)


        try:
            lucid_schema = self._server.query(
                'ProjectSchema where name is "{}"'.format(default_schema_name)).one()

            ft_project = self._server.create('Project', {
                'name': project.id,
                'full_name': slug,
                'project_schema': lucid_schema
            })
            self._logger.debug('Created ftrack project for %s - %s (%s)', project, connection, ft_project)

            # assign the general project scope
            try:
                general_scope = self._server.query("Scope where name is '{}'".format(project.type_code.description)).one()
                ft_project['scopes'].append(general_scope)
            except:
                self._logger.warn("Couldn't assign scope for %s", connection)

            # set the project number custom attribute:
            try:
                ft_project['custom_attributes']['project_id'] = project.id
            except:
                self._logger.warn("Couldn't set project_id custom attribute for %s", connection)

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

            # save the reference to the db
            connection.identifier = ft_project['id']
            connection.state_message = "Created successfully!"
            connection.save()

        except ftrack_api.exception.ServerError or \
            ftrack_api.exception.OperationError or \
            ftrack_api.exception.ConnectionClosedError as err:
            self._logger.error("Couldn't archive %s", connection, exc_info=True)
            # log the state on the connection
            connection.state_message = "Error: {}".format(err)
            connection.save()
            # raising the error will cause the task to be retried
            raise err

    def rename(self, service_connection_id):
        '''
        Rename an ftrack project
        Args:
            project_id (int): the project id number to search for
            new_title (str): the new title for the project including any P-####

        @return success boolean
        '''
        ServiceConnection = apps.get_model("lucid_api", "ServiceConnection")
        connection = ServiceConnection.objects.get(pk=service_connection_id)
        project = connection.project
        
        # generate slug based on the current project name, which has already changed, since
        # we got here via a signal on that change

        new_slug = self._format_slug(connection)

        self._logger.info('Changing ftrack project %s to %s', project, new_slug)

        try:
            ft_project = self._server.get('Project', connection.identifier)
            old_slug = ft_project['full_name']
            ft_project['full_name'] = new_slug
            self._server.commit()
            self._logger.debug('Renamed project %s to %s', old_slug, ft_project['full_name'])

            connection.state_message = "Renamed Successfully to {}".format(new_slug)
            connection.save()

        except ftrack_api.exception.ServerError or \
            ftrack_api.exception.OperationError or \
            ftrack_api.exception.ConnectionClosedError as err:
            self._logger.error("Couldn't archive %s", connection, exc_info=True)
            # log the state on the connection
            connection.state_message = "Error: {}".format(err)
            connection.save()
            # raising the error will cause the task to be retried
            raise err

    def archive(self, service_connection_id):
        '''
        Archive an ftrack project

        Args:
            project_id (int): the project id to archive
        
        Returns:
            bool: Success or not
        '''
        ServiceConnection = apps.get_model("lucid_api", "ServiceConnection")
        connection = ServiceConnection.objects.get(pk=service_connection_id)
        project = connection.project
        self._logger.info('Archiving ftrack project for %s', project )

        try:
            # archive in ftrack
            ft_project = self._server.get("Project", connection.identifier)
            ft_project['status'] = 'hidden'
            self._server.commit()
            # update the db
            connection.state_message = "Archived successfully!"
            connection.save()
            # log it
            self._logger.info('Status for project %s has been set to %s.', project_id, project['status'])
        except ftrack_api.exception.ServerError or \
            ftrack_api.exception.OperationError or \
            ftrack_api.exception.ConnectionClosedError as err:
            self._logger.error("Couldn't archive %s", connection, exc_info=True)
            # log the state on the connection
            connection.state_message = "Error: {}".format(err)
            connection.save()
            # raising the error will cause the task to be retried
            raise err

    def unarchive(self, service_connection_id):
        '''
        un-archives the ftrack project
        '''

        ServiceConnection = apps.get_model("lucid_api", "ServiceConnection")
        connection = ServiceConnection.objects.get(pk=service_connection_id)
        project = connection.project
        self._logger.info('Unarchiving ftrack project for %s', project )

        try:
            # archive in ftrack
            ft_project = self._server.get("Project", connection.identifier)
            ft_project['status'] = 'active'
            self._server.commit()
            # update the db
            connection.state_message = "Unarchived successfully!"
            connection.save()
            # log it
            self._logger.info('Status for project %s has been set to %s.', project_id, project['status'])
        except ftrack_api.exception.ServerError or \
            ftrack_api.exception.OperationError or \
            ftrack_api.exception.ConnectionClosedError as err:
            self._logger.error("Couldn't archive %s", connection, exc_info=True)
            # log the state on the connection
            connection.state_message = "Error: {}".format(err)
            connection.save()
            # raising the error will cause the task to be retried
            raise err

    def get_link(self, service_connection_id):
        '''
        Generates a deep-link into the ftrack client for the project
        
        Args:
            project_id (int): the project_id number to get a link for

        Returns:
            str: URL for the project
        '''
        ServiceConnection = apps.get_model("lucid_api", "ServiceConnection")
        connection = ServiceConnection.objects.get(pk=service_connection_id)
        
        self._logger.info('Get link for %s', connection)

        try:
            url = "{server}/#entityType=show&entityId={connection.identifier}&itemId=projects&view=tasks".format(
                connection=connection,
                server=self._server.server_url
            )
            self._logger.debug('Link created for project %s: %s ', project_id, url)
            return url
        except:
            self._logger.error("Couldn't get link for %s", connection, exc_info=True)


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

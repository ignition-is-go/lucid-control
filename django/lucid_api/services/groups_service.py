'''
Google Groups Service

for Lucid Control

JT
06/26/2017
'''

import service_template
import httplib2, json
import os
import re
from apiclient import discovery, errors
from oauth2client.service_account import ServiceAccountCredentials

from django.apps import apps
from celery.utils.log import get_task_logger


class Service(service_template.ServiceTemplate):
    _DEFAULT_REGEX = re.compile(r'^(?P<typecode>[A-Z])-(?P<project_id>\d{4})')
    _DEFAULT_FORMAT = "{typecode}-{project_id:04d}-{connection_name}"
    _pretty_name = "Google Groups"
   
    def __init__(self):
        '''
        Creates necessary services with Google Admin and Groups; also setups the logger.
        '''

        self._logger = get_task_logger(__name__)
        self._admin = self._create_admin_service()
        self._group = self._create_groupsettings_service()

    def create(self, service_connection_id):
        '''
        Creates Google Groups Group and adds necessary users to it.
        '''

        group = self._admin.groups()
        grp_settings = self._group.groups()
        ServiceConnection = apps.get_model("lucid_api", "ServiceConnection")
        connection = ServiceConnection.objects.get(pk=service_connection_id)
        project = connection.project

        self._logger.info('Start Create Create Google Group for %s: %s',connection, project.title)
        create_success = False
        
        slug = self._format_slug(connection)

        grp_info = {
            "email" : "{}@lucidsf.com".format(slug), # email address for the group
            "name" : self._format_email_name(connection), # group name
            "description" : "Group Email for {}".format(slug), # group description
        }

        # Setup our default settings.
        dir_info = {
            "showInGroupDirectory" : "true", # let's make sure this group is in the directory
            "whoCanPostMessage" : "ANYONE_CAN_POST", # this should be the default but...
            "allowExternalMembers" : "true",
            "whoCanViewMembership" : "ALL_IN_DOMAIN_CAN_VIEW", # everyone should be able to view the group
            "includeInGlobalAddressList" : "true", # In case anyone decides to become an Outlook user
            "isArchived" : "true", # We want to keep all the great messages
        }

        try:
            # make the group via google api
            create_response = group.insert(body=grp_info).execute()
            create_settings = grp_settings.patch(groupUniqueId=grp_info['email'], body=dir_info).execute() 
            
            # store the email as the identifier in django
            connection.identifier = grp_info['email']
            connection.state_message = "Created Successfully!"
            connection.save()

            self._logger.info('Created Google Group %s with email address %s', grp_info['name'], grp_info['email'])
            self._logger.debug('Create response = %s', create_response)
        except errors.HttpError as err:
            self._logger.error(err.message)
            if err.resp.status == 409:
                # Group already exists
                connection.state_message = "Group already exists! {}".format(err)
                connection.save()
            else:
                raise GroupsServiceError(err)

        # With the group created, let's add some members.
        emp_group = self.list_employees()

        # don't add users for test projects
        if project.type_code.character_code == "X":
            return 

        try: 
            for i in emp_group:
                add_users = self._admin.members().insert(groupKey=grp_info['email'], body=({'email' : i})).execute()
                self._logger.debug('Added %s to %s', i, grp_info['name']) 
        except errors.HttpError as err:
            self._logger.error('Failed try while adding members: {}'.format(err))
            raise GroupsServiceError('Problem adding members to group!')

        return 

    def rename(self, service_connection_id):
        '''
        Renames an existing google group.
        '''

        ServiceConnection = apps.get_model("lucid_api", "ServiceConnection")
        connection = ServiceConnection.objects.get(pk=service_connection_id)
        project = connection.project

        slug = self._format_slug(connection)

        # trim dangling "-"
        if slug[-1]=="-": slug = slug[0:-1]

        self._logger.info('Start Rename Google Group for Project# %s to %s', project.id, slug)
        
        group = self._admin.groups()
        # 2. Create the JSON request for the changes we want
        grp_info = {
            # We leave out 'email' because we want the address to remain the same.
            # new group name
            "name" : self._format_email_name(connection), 
            "description" : "Group Email for {}".format(slug), # new group description
        } 

        # 3. Perform actual rename here. 
        try:
            create_response = self._admin.groups().patch(
                groupKey=connection.identifier,
                body=grp_info
                ).execute()

            self._logger.debug("Renamed %s to %s", connection, slug)

            connection.state_message = "Renamed successfully!"
            connection.save()
        except GroupsServiceError as err:
            self._logger.error('Unable to rename group %s to %s', connection.identifier, new_title)
            connection.state_message = "Unable to rename: {}".format(err)
            connection.save()
            raise GroupsServiceError('Unable to rename group %s to %s', connection, new_title)

    def archive(self, service_connection_id):
        '''

        Archives an existing google group. (Read: Change archiveOnly to true.)

        :param project_id: The ID of the project you want to archive.
        :type str:
        :return: True or False
        :type bool:
        '''
        # 1. get info from database
        ServiceConnection = apps.get_model("lucid_api", "ServiceConnection")
        
        try:
            connection = ServiceConnection.objects.get(pk=service_connection_id)
            project = connection.project
            group_name = self._format_email_name(connection)
            self._logger.info("Started Archive for %s", connection)

        except Exception as err:
            self._logger.error("Couldn't get service connection %s from DB", service_connection_id, exc_info=True)
            raise GroupsServiceError("Can't archive connection %s", service_connection_id)
        
        grp_settings = self._group.groups()

        dir_info = { 
            "archiveOnly" : "true", # archive that bad boy
            "whoCanPostMessage" : "NONE_CAN_POST", # this is a requirement for archiveOnly
            "includeInGlobalAddressList" : "true", # don't need this anymore
        }
        
        # 2. issue the command to google's api
        try:
            create_settings = grp_settings.patch(
                groupUniqueId=connection.identifier, 
                body=dir_info).execute()

            connection.state_message = "Archived successfully!"
            connection.save()
            self._logger.info("Archived %s.", connection)
            
        except GroupsServiceError as err:
            self._logger.error("Unable to archive %s.", connection, exc_info=True)
            connection.state_message = "Unable to archive : {}".format(err)
            connection.save()
            raise GroupsServiceError("Ack! Can't archive %s: %s", connection, err.message)
        

    def _format_slug(self, connection):
        '''
        Formats the slug based on the connection data.

        ### Args:
        - **connection**: a *connection* model object from lucid-api
        '''

        slug = super(Service, self)._format_slug(connection).replace(" ","-").strip("-")

        self._logger.info("Email Slug=%s", slug)
        return slug

    def _format_email_name(self, connection):
        '''
        formats the directory name for the email based on the connection
        
        {ProjectID}-{ProjectTitle} | {connection_name}
        '''

        name = "{} | {}".format(
            connection.project.__str__(), 
            connection.connection_name
            ).strip("| ")

        return name


    # NOTE: shouldn't need this now that we have a database KJB 12/18/17
    # def _find(self, project_id):
    #     '''

    #     Get a pointer to the project_id for the requested project.

    #     :param project_id: The ID of the project you want to locate.
    #     :type str:
    #     :return:
    #     '''

    #     if not project_id:
    #         self._logger.error('No project ID supplied to _find.')
    #         return

    #     self._logger.info('Attempting to find project ID {id}'.format(id=project_id))

    #     group = self._admin.groups()
    #     response = group.list(customer='my_customer').execute()

    #     for i in response['groups']:
    #         if re.match(i['email'], r'^P-0*(?P<project_id>\d+)@', re.IGNORECASE):
    #             # TODO: Is this actually returning an object? If not, how do we make an instance of this to return?
    #             self._logger.info('Found project ID {id} in {em}.'.format(id=project_id, em=i['email']))
    #             return response['groups']['email'][i]

    #     self._logger.debug('Unable to find projecft ID {id}.'.format(id=project_id))

    # def get_group_id(self, project_id):
    #     '''
    #     Get the google group id (internal identifier)
    #     '''
    #     group = self._admin.groups()

    #     response = group.list(customer='my_customer').execute()
    #     project_id = str(project_id)

    #     for i in response['groups']:
    #         if project_id in i['name']:
    #             return i['id']
        
    #     raise GroupsServiceError("Could not find group #{}".format(project_id))

    # def get_group_email(self, project_id):
    #     '''
    #     Get the google group email address
    #     '''
    #     group = self._admin.groups()

    #     response = group.list(customer='my_customer').execute()
    #     project_id = str(project_id)

    #     group_id = self.get_group_id(project_id)

    #     for i in response['groups']:
    #         if group_id in i['id']:
    #             return i['email']

    #     raise GroupsServiceError("Could not find group_id #{}".format(group_id))

    def list_groups(self):
        '''
        Print a list of groups to stdout
        '''
        group = self._admin.groups()

        response = group.list(customer='my_customer').execute()

        # For debugging purposes only
        # print([r['name'] for r in response['groups']])

        return response
    
    def list_employees(self):
        '''
        Get a list of employees (members of the employees@lucidsf.com group)
        '''
        employee = self._admin.members()
        l = employee.list(groupKey='employees@lucidsf.com').execute()
        
        response = [r['email'] for r in l['members']]
        return response

    def _create_admin_service(self):
        scopes = ['https://www.googleapis.com/auth/admin.directory.group']

        credentials = ServiceAccountCredentials.from_json_keyfile_dict(
            json.loads(os.environ['GOOGLE_SERVICE_AUTH'].replace("'", "\"")),
            scopes=scopes)
        credentials = credentials.create_delegated('developer@lucidsf.com')
        # http = credentials.authorize(httplib2.Http())
        service = discovery.build('admin', 'directory_v1', credentials=credentials)

        return service
    
    def _create_groupsettings_service(self):
        scopes = ['https://www.googleapis.com/auth/apps.groups.settings']

        credentials = ServiceAccountCredentials.from_json_keyfile_dict(
            json.loads(os.environ['GOOGLE_SERVICE_AUTH'].replace("'", "\"")),
            scopes=scopes)
        credentials = credentials.create_delegated('developer@lucidsf.com')
        http = credentials.authorize(httplib2.Http())
        service = discovery.build('groupssettings', 'v1', credentials=credentials)

        return service


class GroupsServiceError(service_template.ServiceException):
    pass
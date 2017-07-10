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

class GroupsService(service_template.ServiceTemplate):
   
    def __init__(self):
        '''
        Creates necessary services with Google Admin and Groups; also setups the logger.
        '''

        self._logger = self._setup_logger(to_file=True)
        self._admin = self._create_admin_service()
        self._group = self._create_groupsettings_service()


    def create(self, project_id, title, silent=False):
        '''
        Creates Google Groups Group and adds necessary users to it.
        '''

        self._logger.info('Start Create Google Group for Project ID %s: %s', project_id, title)

        # service = self._create_admin_service()
        group = self._admin.groups()

        slug = self._format_slug(project_id, title)
        reg = r'^([\w]+-[\w]+)'

        grp_info = {
            "email" : "{}@lucidsf.com".format(re.match(reg, slug).group()), # email address of the group
            "name" : slug, # group name
            "description" : "Group Email for {}".format(slug), # group description
            "showInGroupDirectory" : "true", # let's make sure this group is in the directory
        }

        try:
            create_response = group.insert(body=grp_info).execute()
            self._logger.info('Created Google Group %s (ID: %s) with email address %s', grp_info['name'], project_id, grp_info['email'])
            self._logger.debug(create_response)
        except errors.HttpError as err:
            self._logger.error(err.message)
            if err.resp.status == 409:
                raise GroupsServiceError('Group already exists!')
            else:
                raise GroupsServiceError(err)

# Still need try/except here - also great a loop which cycles through all employees in our directory - use 
        # With the group created, let's add users.
        membs = {
            'email' : 'employees@lucidsf.com'
        }
        add_users = self._admin.members().insert(groupKey=grp_info['email'], body=membs).execute()
        self._logger.debug('Added %s to %s', membs, grp_info['name'])

        return create_response['id']

    def rename(self, project_id, new_title):
        '''
        Renames an existing google group.
        '''

        self._logger.info('Start Rename Google Group for Project ID %s to %s', project_id, new_title)

        # 1. Check to see if the group even exists
        try:
            group_id = get_group_id(project_id)
        except GroupServiceError as err:
            self._logger.debug('Group with project ID %s does not exist.', project_id)
            raise GroupsServiceError("Could not find a project with ID # %s", project_id)
                
        # TODO: change this to use self._admin
        service = _create_admin_service()
        group = service.groups()
        slug = self._format_slug(project_id, new_title)

        # 2. Create the JSON request for the changes we want
        grp_info = {
            "email" : "{}@lucidsf.com".format(slug), # new email address for the group
            "name" : slug, # new group name
            "description" : "Group Email for {}".format(slug), # new group description
        } 

        # 3. Perform actual rename here. Dictionary API
        create_response = service.groups().patch(groupUniqueId=group_id, body=grp_info).execute()
        self._logger.debug("Renamed Group ID %s to %s", project_id, slug)

    
    def archive(self, project_id):
        '''
        Deletes an existing google group.
        '''

        # At last discussion we did not want to archive / delete any google groups so we'll opt out here
        return True

        self._logger.info("Start Delete Google Group for Project ID %s", project_id)

        # 1. Check to see if the group even exists
        try:
            group_id = get_group_id(project_id)
        except GroupServiceError as err:
            self._logger.debug("Group with project ID %s does not exist.", project_id)
            raise GroupsServiceError("Could not find a project with ID # %s", project_id)
        
        service = _create_admin_service
        group = directory.groups()
        
        # 2. Delete the group
        try:
            archive_response = group.delete(group_id).execute()
            self._logger.info("Deleted group with ID # %s", project_id)
            return archive_response.body['ok']
        except GroupsServiceError as err:
            self._logger.error("Unable to delete Google Group with ID # %s", project_id)
            GroupsServiceError("Unable to delete Google Group with ID # %s because: %s", project_id, err.message)

    
    def get_group_id(self, project_id):
        service = _create_admin_service()
        group = service.groups()

        response = group.list(customer='my_customer').execute()

        for i in response['groups']:
            if project_id in i['name']:
                return i['id']
        
        raise GroupsServiceError("Could not find group #{}".format(project_id))
        
    def list_groups(self):
        group = self._admin.groups()

        response = group.list(customer='my_customer').execute()

        # For debugging purposes only
        print([r['name'] for r in response['groups']])
    
    def list_employees(self):
        response = self._admin.members().list('employees@lucidsf.com')

        print([r['name'] for r in response['members']])

    def _create_admin_service(self):
        scopes = ['https://www.googleapis.com/auth/admin.directory.group']

        with open("auths/lucid-control-b5aa575292fb.json",'r') as fp:
            credentials = ServiceAccountCredentials.from_json_keyfile_dict(
                json.load(fp),
                scopes= scopes)
            credentials = credentials.create_delegated('developer@lucidsf.com')
            http = credentials.authorize(httplib2.Http())
            service = discovery.build('admin', 'directory_v1', credentials=credentials)

            return service
    
    def _create_groupsettings_service(self):
        scopes = ['https://www.googleapis.com/auth/admin.directory.group.member']

        with open("auths/lucid-control-b5aa575292fb.json", 'r') as fp:
            credentials = ServiceAccountCredentials.from_json_keyfile_dict(
                json.load(fp),
                scopes= scopes)
            credentials = credentials.create_delegated('developer@lucidsf.com')
            http = credentials.authorize(httplib2.Http())
            service = discovery.build('admin', 'directory_v1', credentials=credentials)

            return service

class GroupsServiceError(service_template.ServiceException):
    pass
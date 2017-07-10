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

        group = self._admin.groups()
        grp_settings = self._group.groups()
        slug = self._format_slug(project_id, title)
        reg = r'^([\w]+-[\w]+)'

        grp_info = {
            "email" : "{}@lucidsf.com".format(re.match(reg, slug).group()), # email address of the group
            "name" : slug, # group name
            "description" : "Group Email for {}".format(slug), # group description
        }

        # Setup our default settings.
        dir_info = {
            "showInGroupDirectory" : "true", # let's make sure this group is in the directory
        }

        try:
            create_response = group.insert(body=grp_info).execute()
            create_settings = grp_settings.patch(groupUniqueId=grp_info['email'], body=dir_info).execute() # This is where I left off - groupUniqueId unexpected arg
            self._logger.info('Created Google Group %s (ID: %s) with email address %s', grp_info['name'], project_id, grp_info['email'])
            self._logger.debug('Create response = %s', create_response)
        except errors.HttpError as err:
            self._logger.error(err.message)
            if err.resp.status == 409:
                raise GroupsServiceError('Group already exists!')
            else:
                raise GroupsServiceError(err)

        # With the group created, let's add some members.
        emp_group = self.list_employees()

        try: 
            for i in emp_group:
                add_users = self._admin.members().insert(groupKey=grp_info['email'], body=({'email' : i})).execute()
                self._logger.debug('Added %s to %s', i, grp_info['name']) 
        except errors.HttpError as err:
            self._logger.error('Failed try while adding members: {}'.format(err))
            raise GroupsServiceError('Problem adding members to group!')

        return create_response['id']

    def rename(self, project_id, new_title):
        '''
        Renames an existing google group.
        '''

        self._logger.info('Start Rename Google Group for Project ID %s to %s', project_id, new_title)

        # 1. Check to see if the group even exists
        try:
            group_id = self.get_group_id(project_id)
        except GroupsServiceError as err:
            self._logger.debug('Group with project ID %s does not exist.', project_id)
            raise GroupsServiceError("Could not find a project with ID # %s", project_id)
        
        group = self._admin.groups()
        slug = self._format_slug(project_id, new_title)

        # 2. Create the JSON request for the changes we want
        grp_info = {
            # We leave out 'email' because we want the address to remain the same.
            "name" : slug, # new group name
            "description" : "Group Email for {}".format(slug), # new group description
        } 

        # 3. Perform actual rename here. 
        try:
            create_response = self._admin.groups().patch(groupKey=group_id, body=grp_info).execute()
            self._logger.debug("Renamed Group ID %s to %s", project_id, slug)
        except GroupsServiceError as err:
            self._logger.error('Unable to rename group %s to %s', project_id, new_title)
            raise GroupsServiceError('Unable to rename group %s to %s', project_id, new_title)

        return ['id']

    
    def archive(self, project_id):
        '''
        Archives an existing google group.
        Read: Change the ShowInDirectory to False.
        '''

        self._logger.info("Started Archive Google Group for Project ID %s", project_id)

        # 1. Check to see if the group even exists
        try:
            group_id = self.get_group_id(project_id)
        except GroupsServiceError as err:
            self._logger.error("Group with project ID %s does not exist.", project_id)
            raise GroupsServiceError("Can't archive, no project ID # %s", project_id)
        
        group = self._admin.groups()
        grp_info = { "showInGroupDirectory" : "false", }
        
        # 2. Remove the group from the directory
        try:
            create_response = self._admin.groups().patch(groupKey=group_id, body=grp_info).execute()
            self._logger.info("Removed group with ID # %s from directory.", project_id)
            return create_response.body['ok']
        except GroupsServiceError as err:
            self._logger.error("Unable to remove Google Group with ID # %s from directory", project_id)
            GroupsServiceError("Ack! Can't remove ID # %s from directory because: %s", project_id, err.message)
        
        return ['id']

    
    def get_group_id(self, project_id):
        group = self._admin.groups()

        response = group.list(customer='my_customer').execute()
        project_id = str(project_id)

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
        employee = self._admin.members()
        l = employee.list(groupKey='employees@lucidsf.com').execute()
        
        response = [r['email'] for r in l['members']]

        # print([r['email'] for r in response['members']])
        return response

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
        scopes = ['https://www.googleapis.com/auth/apps.groups.settings']

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
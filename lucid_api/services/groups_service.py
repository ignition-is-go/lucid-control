'''
Google Groups Service

for Lucid Control

JT
06/26/2017
'''

import service_template
import httplib2, json
import os
from apiclient import discovery
from oauth2client.service_account import ServiceAccountCredentials

class GroupsService(service_template.ServiceTamplate):
   
    def __init__(self, team_token=None, bot_token=None):
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

        service = create_service()
        group = service.groups()

        slug = self._format_slug(project_id, title)

        grp_info = {
            "email" : "{}@lucidsf.com".format(slug), # email address of the group
            "name" : slug, # group name
            "description" : "Group Email for {}".format(slug), # group description
        }

        create_response = service.groups().insert(body=grp_info).execute()
        self._logger.debug('Created Google Group %s (ID: %s) with email address %s', grp_info['name'], project_id, grp_info['email'])
 
        # With the group created, let's add users.
        add_users = service.members().insert(groupKey=grp_info['email'], body="employees@lucidsf.com").execute()
        self._logger.debug('Added %s to %s', body, grp_info['name'])


    
    def rename(self, project_id, new_title):
        pass
    
    def archive(self, project_id):
        pass
    
    def list_groups():
        service = create_service()
        group = service.groups()

        response = group.list(customer='my_customer').execute()

        # For debugging purposes only
        print([r['name'] for r in response['groups']])

    def _create_admin_service():
        scopes = ['https://www.googleapis.com/auth/admin.directory.group']

        with open("auths/lucid-control-b5aa575292fb.json",'r') as fp:
            credentials = ServiceAccountCredentials.from_json_keyfile_dict(
                json.load(fp),
                scopes= scopes)
            credentials = credentials.create_delegated('developer@lucidsf.com')
            http = credentials.authorize(httplib2.Http())
            service = discovery.build('admin', 'directory_v1', credentials=credentials)

            return service
    
    def _create_groupsettings_service():
        scopes = ['https://www.googleapis.com/auth/admin.directory.group.member']

        with open("auths/lucid-control-b5aa575292b.json", 'r') as fp:
             credentials = ServiceAccountCredentials.from_json_keyfile_dict(
                json.load(fp),
                scopes= scopes)
            credentials = credentials.create_delegated('developer@lucidsf.com')
            http = credentials.authorize(httplib2.Http())
            service = discovery.build('admin', 'directory_v1', credentials=credentials)

            return service

        
    


class GroupsServiceException(Exception):
    pass
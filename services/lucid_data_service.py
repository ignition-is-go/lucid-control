'''
Lucid Data Service connector for Lucid Control
Connectes to the custom Django/Postgres database

K Bjordahl
6/21/17
'''

import service_template
import requests
import os
import simplejson as json

class LucidDataService(service_template.ServiceTemplate):

    _pretty_name = "LucidData"

    def __init__(self):

        self._setup_logger()

    def create(self, project_id, title, slack_channel, silent=None):
        '''Creates the database entry on luciddata'''
        self._logger.info("Attempting to create id#%s: %s (slack: %s) on Lucid Data",
            project_id, title, slack_channel)

        slug = self._format_slug(project_id,title)
        headers = {'Content-Type': 'application/json', 'Accept': 'application/json'}
        url = '{}?username={}&api_key={}'.format(os.environ['PROJECT_API_BASE_URL'], os.environ['API_USERNAME'], os.environ['API_KEY'])
        payload = {
            'title': title,
            'slug': slug,
            'slack_channel': slack_channel

        }
        r = requests.post(url, data=json.dumps(payload), headers=headers)
        
        self._logger.info("LucidData response: %s\n\tresponse content: %s", r, r.content)
        return r

    def archive(self, project_id):
        self._logger.info("Attempting to archive id#%s on Lucid Data", project_id)
        headers = {'Content-Type': 'application/json', 'Accept': 'application/json'}
        url = '{}{}/?username={}&api_key={}'.format(os.environ['PROJECT_API_BASE_URL'], project_id, os.environ['API_USERNAME'], os.environ['API_KEY'])
        payload = {
            'production_state': 'archived',
            'sales_state': 'changes complete',
            'invoice_state': 'closed'
        }
        r = requests.put(url, data=json.dumps(payload), headers=headers)
     
        self._logger.info("LucidData response: %s\n\tresponse content: %s", r, r.content)
        return r


    def rename_project(self, project_id, new_title):
        self._logger.info("Attempting to rename id#%s to %s on Lucid Data", project_id, new_title)

        new_slug = self._format_slug(project_id,new_title)
        headers = {'Content-Type': 'application/json', 'Accept': 'application/json'}
        url = '{}{}/?username={}&api_key={}'.format(os.environ['PROJECT_API_BASE_URL'], project_id, os.environ['API_USERNAME'], os.environ['API_KEY'])
        payload = {
            'title': new_title,
            'slug': new_slug
        }
        r = requests.put(url, data=json.dumps(payload), headers=headers)
        
        self._logger.info("LucidData response: %s\n\tresponse content: %s", r, r.content)
        return r


    def get_project_id_from_channel(self, slack_channel):
        self._logger.info("Attempting to get project id from slack channel %s on Lucid Data", slack_channel)

        response = requests.get('{}?format=json&username={}&api_key={}&slack_channel={}'.format(
            os.environ['PROJECT_API_BASE_URL'], 
            os.environ['API_USERNAME'], 
            os.environ['API_KEY'],
            slack_channel
            ))
        project_id = response.json()['objects'][0]['id']

        self._logger.info("Found #%s for slack channel %s", project_id, slack_channel)

        return project_id

    def get_next_project_id(self):
        '''Gets the next available project ID in the database'''
        response = requests.get('{}?format=json&username={}&api_key={}'.format(os.environ['LAST_PROJECT_API_BASE_URL'], os.environ['API_USERNAME'], os.environ['API_KEY']))
        last_project_id = response.json()['objects'][0]['id']
        next_id = last_project_id + 1

        self._logger.info("Got %d as next available project ID from LucidData", next_id)
        return next_id

    def get_link(self, project_id):
        url = '{}{}/change/'.format(os.environ['PROJECT_EDIT_BASE_URL'], project_id)
        return url
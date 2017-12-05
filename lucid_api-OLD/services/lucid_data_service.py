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

        self._logger = self._setup_logger(to_file=True)

    def create(self, title, slack_channel="", silent=None):
        '''Creates the database entry on luciddata'''
        self._logger.info("Attempting to create %s (slack: %s)",
            title, slack_channel)

        slug = self._format_slug(0,title)
        headers = {'Content-Type': 'application/json', 'Accept': 'application/json'}
        url = '{}?username={}&api_key={}'.format(os.environ['PROJECT_API_BASE_URL'], os.environ['API_USERNAME'], os.environ['API_KEY'])
        payload = {
            'title': title,
            'slug': slug,
            'slack_channel': slack_channel

        }
        r = requests.post(url, data=json.dumps(payload), headers=headers)

        if r.status_code == 201:
            # Location looks like '/api/project/128/'
            project_id = r.headers['Location'].rsplit("/",2)[-2]
            return project_id
        else:
            self._logger.error("Got a bad status code: %s Headers: %s", r.status_code, r.headers)
            raise LucidDataServiceError("Got the wrong status code from create: {} [{}]".format(r.status_code, r.headers))

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


    def rename(self, project_id, new_title, slack_channel=""):
        self._logger.info("Attempting to rename id#%s to %s on Lucid Data", project_id, new_title)

        new_slug = self._format_slug(project_id,new_title)
        headers = {'Content-Type': 'application/json', 'Accept': 'application/json'}
        url = '{}{}/?username={}&api_key={}'.format(os.environ['PROJECT_API_BASE_URL'], project_id, os.environ['API_USERNAME'], os.environ['API_KEY'])
        payload = {
            'title': new_title,
            'slug': new_slug
        }

        if slack_channel is not "":
            payload['slack_channel'] = slack_channel

        r = requests.put(url, data=json.dumps(payload), headers=headers)

        if r.status_code in range(200,299):
            self._logger.info("Rename Success!")
            return True
        else:
            self._logger.error("Rename failture. Status: %s", r.status_code)
            raise LucidDataServiceError("Failture. Status: {}".format(r.status_code))

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

    def get_link_dict(self, project_id):
        return {":floppy_disk: "+self.get_pretty_name() : self.get_link(project_id)}


class LucidDataServiceError(Exception):
    pass
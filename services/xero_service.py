'''
Xero Service Connector
for Lucid Control

K. Bjordahl
6/20/17
'''

from xero import Xero 
from xero.auth import PrivateCredentials
import logging, re
import constants
from service_template import ServiceTemplate

class XeroService(ServiceTemplate):

    def __init__(self, slug_regex=super()._DEFAULT_REGEX):
        credentials = PrivateCredentials(constants.XERO_CONSUMER_KEY, constants.XERO_API_PRIVATE_KEY)
        self._xero = Xero(credentials)
        self._logger = logging.getLogger(__name__)
        self._slug_regex = slug_regex
        
    def create(self, project_id, title):
        '''
        Creates a new Xero tracking category
        '''
        self._xero.populate_tracking_categories()
        try:
            response = self._xero.TCShow.options.put({'Name': text.lower()})
            return True
            #TODO: figure out if the action was a success
        except Exception as e:
            raise e
        
    def rename(self, project_id, new_title):
        '''
        Rename the Xero tracking category with the project_id
        '''
        option = self._find(project_id)
        option['Name'] = self._format_slug(project_id, new_title)
        try:
            response = xero.TCShow.options.save({'TrackingOptionID': option['TrackingOptionID'], 'Name': option['Name']})
            return True
        except Exception as e:
            raise e


    def archive(self, project_id):
        '''
        Archive the tracking category for project_id
        '''
        option = self._find(project_id)
        
        option['IsArchived'] = True
        try:
            response = xero.TCShow.options.delete(option['TrackingOptionID'])
            return True
        except Exception as e:
            raise e


    def _find(self, project_id):
        '''
        finds a xero tracking category by project_id

        Args:
            project_id (int): Project ID number to search for
        
        Returns:
            str: Xero tracking category option ID (or False)
        '''
        self._xero.populate_tracking_categories()

        self._logger.info("Starting search for %s", str(project_id))
        for option in self._xero.TCShow.options.all():
            self._logger.debug("Checking Xero option %s (%s)", option['name'], option)
            m = re.match(self._slug_regex, option['name'])
            if int(m.group("project_id")) == project_id:
                self._logger.info("Matched %s (%s)", option['name'], option)
                return option
            
        self._logger.error("Couldn't find Xero option matching %s", str(project_id))
        raise XeroServiceError("Couldn't find Xero option matching {}".format(project_id))
        
        
class XeroServiceError(Exception):
    pass
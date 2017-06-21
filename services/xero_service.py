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

DEFAULT_REGEX = r'^P-(?P<project_id>\d{4})-(?P<project_title>.+)'

class XeroService():

    def __init__(self, slug_regex=DEFAULT_REGEX):
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
        
    def _find(self, project_id):
        '''
        finds a xero tracking category by project_id

        Args:
            project_id (int): Project ID number to search for
        
        Returns:
            str: Xero tracking category option ID (or False)
        '''
        self._xero.populate_tracking_categories()
        option_id = False

        self._logger.info("Starting search for %s", str(project_id))
        for option in self._xero.TCShow.options.all():
            self._logger.debug("Checking Xero option %s (%s)", option['name'], option)
            m = re.match(self._slug_regex, option['name'])
            if int(m.group("project_id")) == project_id:
                self._logger.info("Matched %s (%s)", option['name'], option)
                option_id = option['TrackingOptionID']
            else:
                self._logger.error("Couldn't find Xero option matching %s", str(project_id))
                raise XeroServiceError("Couldn't find Xero option matching {}".format(project_id))
        
        return option_id
        
class XeroServiceError(Exception):
    pass
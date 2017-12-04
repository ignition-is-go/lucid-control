'''
Xero Service Connector
for Lucid Control

K. Bjordahl
6/20/17
'''

from xero import Xero 
from xero.auth import PrivateCredentials
import logging
import re
import service_template 
import os

class XeroService(service_template.ServiceTemplate):

    _pretty_name = "Xero"

    def __init__(self, slug_regex=None):
        '''
        Creates and connects to a new Xero instance
        '''
        if slug_regex is not None:
                self._DEFAULT_REGEX = slug_regex
        
        credentials = PrivateCredentials(os.environ.get('XERO_CONSUMER_KEY'), os.environ.get('XERO_API_PRIVATE_KEY'))
        self._xero = Xero(credentials)
        
        self._logger = self._setup_logger(level='debug', to_file=True)
        
        self._omit = os.environ['XERO_OMIT']
        
    def create(self, project_id, title, silent=None):
        '''
        Creates a new Xero tracking category
        '''
        if self._omit: return True
        
        self._logger.info("Attempting to create Xero category for #%s",project_id)
        slug = self._format_slug(project_id, title)
        #check if the tracking category exists:
        try:
            search = self._find(project_id)
        except XeroServiceError:
            self._logger.info("Confirmed that % doesn't exist", project_id)
            try:
                response = self._xero.TCShow.options.put({'Name': slug})
                self._logger.info("Finished Creating # %s: %s", project_id, response)
                search_results = self._find(project_id)
                return bool(slug==search_results['Name'])
                #TODO: figure out if the action was a success
            except Exception as e:
                raise e

        else:
            #we found the tracking category, so just return
            self._logger.error("Looks like %s already exists", project_id)
            raise XeroServiceError("A tracking category for {} already exists".format(project_id))
            return True

        
        
    def rename(self, project_id, new_title):
        '''
        Rename the Xero tracking category with the project_id
        '''
        if self._omit: return True

        self._logger.info("Attempting to rename Xero category for #%s to %s", project_id, new_title)

        try:
            option = self._find(project_id)
        except XeroServiceError as err:
            self._logger.info("It seems that % doesn't exist", project_id)
            raise err

        new_slug = self._format_slug(project_id, new_title)
        option['Name'] = new_slug

        try:
            response = self._xero.TCShow.options.save({'TrackingOptionID': option['TrackingOptionID'], 'Name': option['Name']})
            self._logger.info("Finished renaming # %s: %s", project_id, response)
            return bool(new_slug==response[0]['Name'])
        except Exception as e:
            raise e


    def archive(self, project_id):
        '''
        Archive the tracking category for project_id
        '''
        if self._omit: return True

        self._logger.info("Attempting to archive Xero category for #%s", project_id)

        try:
            option = self._find(project_id)
        except XeroServiceError as err:
            self._logger.info("It seems that %s doesn't exist", project_id)
            raise err
            
        option['IsArchived'] = True
        try:
            response = self._xero.TCShow.options.delete(option['TrackingOptionID'])
            self._logger.info("Finished archiving # %s: %s", project_id, response)
            return bool(option['TrackingOptionID']==response[0]['TrackingOptionID'])
        except Exception as e:
            raise e


    def get_link(self, project_id):
        return ""


    def _find(self, project_id):
        '''
        finds a xero tracking category by project_id

        Args:
            project_id (int): Project ID number to search for
        
        Returns:
            str: Xero tracking category option ID (or False)
        '''
        self._xero.populate_tracking_categories()
        project_id = int(project_id)

        self._logger.info("Starting search for %s", str(project_id))
        for option in self._xero.TCShow.options.all():
            self._logger.debug("Checking Xero option %s (%s)", option['Name'], option)
            m = re.match(self._DEFAULT_REGEX, option['Name'])
            if m is None:
                continue
            elif int(m.group("project_id")) == project_id:
                self._logger.info("Matched %s (%s)", option['Name'], option)
                return option
            
        self._logger.error("Couldn't find Xero option matching %s", str(project_id))
        raise XeroServiceError("Couldn't find Xero option matching {}".format(project_id))
        
    
class XeroServiceError(service_template.ServiceException):
    pass
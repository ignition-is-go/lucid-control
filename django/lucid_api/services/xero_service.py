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

from django.apps import apps
from celery.utils.log import get_task_logger

task_logger = get_task_logger(__name__)

class Service(service_template.ServiceTemplate):

    _pretty_name = "Xero"

    def __init__(self, slug_regex=None):
        '''
        Creates and connects to a new Xero instance
        '''
        if slug_regex is not None:
            self._DEFAULT_REGEX = slug_regex
        
        credentials = PrivateCredentials(os.environ.get('XERO_CONSUMER_KEY'), os.environ.get('XERO_API_PRIVATE_KEY'))
        self._xero = Xero(credentials)
        self._xero.populate_tracking_categories()
        
        self._logger = task_logger
        
        self._omit = True if os.environ['XERO_OMIT'] == "True" else False
        self._logger.info("Xero Omit == %s", self._omit)

    def create(self, service_connection_id):
        '''
        Creates a new Xero tracking category
        '''
        self._logger.info("Xero Omit == %s", self._omit)
        if self._omit: return True

        ServiceConnection = apps.get_model("lucid_api", "ServiceConnection")
        connection = ServiceConnection.objects.get(pk=service_connection_id)
        project = connection.project
        
        self._logger.info("Attempting to create Xero category for %s",project)
        slug = self._format_slug(connection)
   
        try:
            # create the tracking category
            response = self._xero.TCShow.options.put({'Name': slug})

            # update the DB
            connection.identifier = response[0]['TrackingOptionID']
            connection.save()

            self._logger.info("Finished Creating Xero tracking category %s:: %s", slug, response)

        except Exception as e:
            # when we fail to create Xero, just delete.
            connection.delete()
            raise e

        return
        
        
    def rename(self, service_connection_id):
        '''
        Rename the Xero tracking category with the project_id
        '''
        self._logger.info("Xero Omit == %s", self._omit)
        if self._omit: return True

        ServiceConnection = apps.get_model("lucid_api", "ServiceConnection")
        connection = ServiceConnection.objects.get(pk=service_connection_id)
        project = connection.project
        
        self._logger.info("Attempting to rename Xero category for #%s to %s", project_id, new_title)

        new_slug = self._format_slug(project_id, new_title)

        try:
            response = self._xero.TCShow.options.save({'TrackingOptionID': option['TrackingOptionID'], 'Name': new_slug})
            self._logger.info("Finished renaming Xero Tracking Category %s :: %s", new_slug, response)
        except Exception as e:
            raise e

        return


    def archive(self, service_connection_id):
        '''
        Archive the tracking category for project_id
        '''
        self._logger.info("Xero Omit == %s", self._omit)
        if self._omit: return True

        ServiceConnection = apps.get_model("lucid_api", "ServiceConnection")
        connection = ServiceConnection.objects.get(pk=service_connection_id)
        project = connection.project

        self._logger.info("Attempting to archive Xero category for #%s", project_id)

        try:
            response = self._xero.TCShow.options.delete(connection.identifier)[0]
            success = (response['IsArchived'] or response['IsDeleted']) and not response['IsActive']
            # update db
            connection.is_archived = success
            self._logger.info("Finished archiving Xero Tracking Category %s :: %s", project, success)
        except Exception as e:
            raise e


    def get_link(self, project_id):
        return ""
        
    
class XeroServiceError(service_template.ServiceException):
    pass
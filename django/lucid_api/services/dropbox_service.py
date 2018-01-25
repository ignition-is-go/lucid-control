'''
Dropbox service connector for lucid control (LucidAPI)

K Bjordahl
6/22/17
'''

import service_template
import dropbox
import simplejson as json
import os
import re
import logging
import datetime
import copy

from django.apps import apps
from celery.utils.log import get_task_logger

class Service(service_template.ServiceTemplate):

    _pretty_name = "Dropbox"
    _DEFAULT_REGEX = re.compile(r'^(?P<typecode>[A-Za-z])-(?P<project_id>\d{4})-(?P<project_title>[^\/]+)\/(?P<connection_name>.+)')
    _DEFAULT_FORMAT = "{typecode}-{project_id:04d}-{title}/{connection_name}"

    FILESAFE_REGEX = r'[\\/:*?\"<>|]+'

    def __init__(self):

        self._logger = get_task_logger(__name__)
        self._logger.info("Instantiated Dropbox!")

        self._dbx = dropbox.Dropbox(os.environ.get('DROPBOX_ACCESS_TOKEN'))
        
    def create(self, service_connection_id):
        '''
        Creates dropbox folder based on the schema in the ENV
        '''
        ServiceConnection = apps.get_model("lucid_api", "ServiceConnection")
        connection = ServiceConnection.objects.get(pk=service_connection_id)
        project = connection.project

        slug = self._format_slug(connection)
        root = os.environ.get('DROPBOX_APP_ROOT')

        self._logger.info('Attempting to create Dropbox folder %s/%s', root, slug)
                
        try:
            # make the folder
            response = self._dbx.files_create_folder( slug )
            self._logger.debug("Dbx Response: %s", response)

            connection.identifier = response.id
            connection.state_message = "Created Successfully!"
            connection.save()
        
        except dropbox.exceptions.InternalServerError or dropbox.exceptions.HttpError as err:
            self._logger.error("Dropbox Error!", exc_info=True)
            connection.state_message = "Error: {}".format(err)
            connection.save()
            raise err

        except Exception as err:
            self._logger.error("Non-retry error:", exc_info=True)
            connection.state_message = "Error: {}".format(err)
            connection.save()

    def rename(self, service_connection_id):
        '''
        renames dropbox folder 
        '''

        ServiceConnection = apps.get_model("lucid_api", "ServiceConnection")
        connection = ServiceConnection.objects.get(pk=service_connection_id)
        project = connection.project

        slug = self._format_slug(connection)

        self._logger.info('Attempting to rename Dropbox folder for %s: %s',
            project, connection)

        try:
            meta = self._dbx.files_get_metadata(connection.identifier)
            self._logger.debug("Got Dropbox Metadata: %s", meta)

            # move from the current path (via metadata) to the new slug path
            response = self._dbx.files_move(meta.path_lower, slug)

            if response.path_display <> slug:
                raise DropboxServiceError("Move failed.")
            else:
                connection.state_message = "Moved successfully to {}".format(slug)
                connection.save()

        except DropboxServiceError as err:
            self._logger.error("Couldn't move folder %s to %s", connection.identifier, slug, exc_info=True)
            connection.state_message = "Error: {}".format(err)
            connection.save()
            raise err
        
        except dropbox.exceptions.InternalServerError or dropbox.exceptions.HttpError as err:
            self._logger.error("Dropbox Error!", exc_info=True)
            connection.state_message = "Error: {}".format(err)
            connection.save()
            raise err

        except Exception as err:
            self._logger.error("Non-retry error:", exc_info=True)
            connection.state_message = "Error: {}".format(err)
            connection.save()
    
    def archive(self, service_connection_id):
        '''
        Archives the folder by moving the project folder into the archive root. 
        Also checks to see if it has already been archived and avoids the duplication of effort.
    
        '''
        ServiceConnection = apps.get_model("lucid_api", "ServiceConnection")
        connection = ServiceConnection.objects.get(pk=service_connection_id)
        project = connection.project

        # slug will generate the correct target folder based on whether or not the connection is archived
        slug = self._format_slug(connection)

        # remove the connection.connection_name from the slug to get the target project folder
        target_folder = slug.rstrip("/"+connection.connection_name.lower())
        self._logger.debug("Target archive folder is %s", target_folder)

        meta = self._dbx.files_get_metadata(connection.identifier)

        if target_folder in meta.path_lower:
            # this folder has already been moved to the target folder
            return
        
        else:
            try:
                # get the project folder by stripping connection.connection_name from the path
                project_folder = meta.path_lower.rstrip("/"+connection.connection_name.lower())
                # move project folder to the target folder
                response = self._dbx.files_move(project_folder, target_folder)

                if target_folder not in response.path_lower:
                    # folder hasn't moved to the correct spot
                    raise DropboxServiceError("Archive failed")
                
                connection.state_message = "{} Success!".format("Archive" if connection.is_archived else "Unarchive")
                connection.save()

            except DropboxServiceError as err:
                self._logger.error("Couldn't move folder %s to %s", connection.identifier, slug, exc_info=True)
                connection.state_message = "Error: {}".format(err)
                connection.save()
                raise err
            
            except dropbox.exceptions.InternalServerError or dropbox.exceptions.HttpError as err:
                self._logger.error("Dropbox Error!", exc_info=True)
                connection.state_message = "Error: {}".format(err)
                connection.save()
                raise err

            except Exception as err:
                self._logger.error("Non-retry error:", exc_info=True)
                connection.state_message = "Error: {}".format(err)
                connection.save()

    def unarchive(self, service_connection_id):
        '''
        Unarchives the folder by moving the project folder into the active root using self.archive
        
        *With Dropbox, unarchiving is the same logic as archiving,
        but we move into a different root folder, as determined by the archive state
        on the service connection. So, we just redirect this to the archive method!*

        '''
        self._logger.info('Attempting to unarchive Dropbox folder via rename...')
        self.archive(service_connection_id)


    def _format_slug(self, connection,):
        '''Correctly formats  the slug for drobox'''
        # do the default one but replace spaces
        slug = super(Service, self)._format_slug(connection).replace(" ", "-")
        # remove non-filesafe chars
        re.sub(self.FILESAFE_REGEX,'',slug)

        # prepend the root, using the active unless is_archived
        if connection.is_archived:
            root = os.environ.get("DROPBOX_APP_ARCHIVE")
        else:
            root = os.environ.get("DROPBOX_APP_ROOT")

        slug = self._join_path(root, slug).lower()

        return slug

    def _get_parent_folder(self, connection):
        '''
        get the parent folder of the connection
        '''
        meta = self._dbx.files_get_metadata(connection.identifier)

        # first count the number of slashes in the current connection name
        slash_count = connection.connection_name..rstrip().rstrip("/").count("/")

        
        



    def _join_path(self, *args):
        '''Fixes paths to uniformly linux style'''
        fixed_path = os.path.join(*args).replace("\\","/")
        self._logger.debug("Path is= %s",fixed_path)
        return fixed_path

    
    # TODO: Need to figure out how this gets used
    # def get_link_dict(self, conn):
    #     '''returns a dictionary of folder: link'''
    #     try:
            
    #         response = {}
    #         meta = self._dbx.files_get_metadata()

    #         return response
            
    #     except Exception as err:
    #         self._logger.error("Had an error getting the link dicitonary: %s", err.message)

class DropboxServiceError(service_template.ServiceException):
    pass
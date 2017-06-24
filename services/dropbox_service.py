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
import constants
import logging
import datetime
from werkzeug.urls import url_fix

os.path.normpath

class DropboxService(service_template.ServiceTemplate):

    _pretty_name = "Dropbox"
    def __init__(self):

        self._logger = self._setup_logger(to_file=True)
        self._logger.info("Instantiated Dropbox!")

        self._dbx = dropbox.Dropbox(constants.DROPBOX_ACCESS_TOKEN)
        
    def create(self, project_id, title, silent=None):
        '''
        Creates dropbox folder based on the schema in the ENV
        '''
        project_id = str(project_id)
        self._logger.info('Attempting to create Dropbox folder schema for #%s: %s',
            project_id, title)
        
        slug = self._format_slug(project_id,title)
        schema = self._get_schema()

        responses = []
        try:
            for f in range(0, len(schema['folders'])):
                folder = schema['folders'][f]
                try:
                    # look for the folder before making it
                    self._logger.debug("Checking for existing in %s/",folder['root'])
                    schema['folders'][f]['match'] = self._find_in_folder(project_id,
                        folder['root'],
                        title=title
                        )

                except DropboxServiceError:
                    # didn't find the folder, so create it
                    self._logger.debug("None found for existing in %s/",folder['root'])
                    to_create = self._join_path(folder['root'], slug)
                    self._logger.info( 'attempting to make: %s', to_create )
                    response = self._dbx.files_create_folder( to_create )
                    self._logger.debug("Dbx Response: %s", response)
                    schema['folders'][f]['match'] = [response]
                    responses.append(bool(
                        response.path_lower == to_create.lower()
                    ))

                finally:
                    # we can create subfolders safely
                    for subfolder in folder['subfolders']:
                        sub_path = self._join_path(folder['root'], slug, subfolder)
                        self._logger.info('attempting to make: %s', 
                            sub_path)
                        response = self._dbx.files_create_folder(sub_path)
                        self._logger.debug("Dbx Response: %s", response)
                        responses.append(bool(
                            response.path_lower == sub_path.lower()
                        ))

            self._logger.info("!!!CREATE RESULTS==%s", responses)
            return not bool(False in responses)

        except Exception as err:
            self._logger.error("Error while creating dropbox folders for #%s: %s",
                project_id, err.message)
            raise err

        # else:
        #     self._logger.error("Cannot create folders for #%s, these already exist: %s",
        #         project_id, folders)
        #     raise DropboxServiceError("Cannot create folders, these already exist: %s", 
        #         folders)

    def rename(self, project_id, title):
        '''
        renames dropbox folder based on the schema in the ENV
        '''
        self._logger.info("-=-=-=-=-=-=-=-=-=-=-=")
        self._logger.info('Attempting to rename Dropbox folder schema for #%s to %s',
            project_id, title)

        try:
            schema = self._find_schema(project_id)
        except DropboxServiceError as err:
            # this means the folders don't exist, so bail!
           raise err
        else:
            self._logger.debug("Found at least one folder.")
            responses = []
            new_slug = self._format_slug(project_id, title)
            
            try:
                for f in range(0, len(schema['folders'])):
                    for folder in schema['folders'][f]['matches']:
                        # assert isinstance(folder, dropbox.files.FolderMetadata)
                        self._logger.debug("Working on %s",folder)
                        path_parts = folder.path_lower.split("/")
                        if not (path_parts[-1].lower() == folder.name.lower()):
                            continue
                        path = "/".join(path_parts[0:-1])
                        rename_target = self._join_path(path, new_slug)
                        self._logger.debug("Attempting to rename %s to %s",
                            folder.path_lower, rename_target)
                        response = self._dbx.files_move(
                            folder.path_lower,
                            rename_target
                            )
                        responses.append(bool(
                            response.path_lower == rename_target.lower()
                        ))

                        self._logger.debug("Rename result: %s (%s)", 
                            responses[-1],
                            response)
                self._logger.info("Finished with rename. Results: %s",responses)
                return not bool(False in responses)
        
            except Exception as err:
                self._logger.error("Error while creating dropbox folders for #%s: %s",
                    project_id, err.message)
                raise err

    
    def archive(self, project_id):
        '''Archives the folders associated with the project'''
        self._logger.info('Attempting to archive Dropbox folder schema for #%s',
            project_id)

        try:
            schema = self._find_schema(project_id)
        except DropboxServiceError as err:
            # this means the folders don't exist, so bail!
            self._logger.error("Couldn't find folders for %s: %s",project_id,err.message)
            raise err

        try:
            responses = []
            year = datetime.date.today().year
            self._logger.debug("Got Schema, archiving as year=%s", year)
            
            for folder in schema['folders']:
                for match in folder['matches']:
                    assert isinstance(match, dropbox.files.FolderMetadata)
                    archive_target = self._join_path(
                        schema['archive'],
                        year,
                        folder['archive_target'],
                        match.name
                    )
                    
                    self._logger.debug("Attempting to move %s to %s", folder.path_lower, archive_target)

                    response = self._dbx.files_move(
                        folder.path_lower,
                        archive_target
                        )
                    
                    responses.append(bool(
                        response.path_lower == rename_target.lower()
                    ))

                    self._logger.debug("!!!Move result: %s (%s)", 
                        responses[-1],
                        response)
            self._logger.info("Finished with archive. Results: %s",responses)
            return not bool(False in responses)
    
        except Exception as err:
            self._logger.error("Error while creating dropbox folders for #%s: %s",
                project_id, err.message)
            raise err


    def _get_schema(self):
        '''Gets the dropbox schema'''
        schema = json.loads(os.environ['DROPBOX_FOLDER_SCHEMA'])
        return schema

    def _find_schema(self, project_id, title=""):
        '''
        Finds all the dropbox folders associated with this project
        '''
        self._logger.info("Starting Search in Dropbox for #%s", project_id)

        # using the default format for dropbox, we ditch the title to give an easy match
        project_code = self._format_slug(project_id,"")

        schema = self._get_schema()
        matches = []
        error = None
        
        for f in range(0,len(schema['folders'])):
            folder = schema['folders'][f]
            try:
                results = self._find_in_folder(project_id, folder['root'], title=title)
                self._logger.info('Found drobox folder matching #%s: %s',
                    project_id, results)
                
                schema['folders'][f]['matches'] = results
            except DropboxServiceError as err:
                error = DropboxServiceError("Found no Folders for {}".format(project_id))

            except dropbox.exceptions.DropboxException as dbx_err:
                self._logger.error("Had a problem with dropbox: %s",
                    dbx_err.message)

        if error is not None:
            raise error  
        else: return schema


    def _find_in_folder(self, project_id, search_root, title=""):
        '''iterates through a folder and returns the folders that match the project id'''
        self._logger.info("Searching %s for %s",search_root,project_id)
        try:
            slug = self._format_slug(project_id,title)
            files = self._dbx.files_list_folder(search_root).entries
            matches = []
            for f in files:
                if f.name.startswith(slug):
                    self._logger.debug("Found %s", f.name)
                    matches.append(f)
            if len(matches) == 0:
                raise DropboxServiceError("Nothing found for {} in {}".format(
                    project_id, search_root
                )) 
            return matches

        except Exception as err:
            raise err

    def _find(self, project_id, title="" ,root=""):
        '''
        search using the dropbox search function
        
        NOTE: this will not find files which are very recently changed, due to indexing on Dropbox
        '''

        project_code = self._format_slug(project_id,title)
        self._logger.info("Searching for [%s] in '%s'",project_code,root)
        self._dbx.files
        search = self._dbx.files_search(root, project_code)   
        results = []
        self._logger.debug("Search Results: %s", search)
        for result in search.matches:
            # if not isinstance(result, dropbox.files.SearchMatch): continue
            if result.match_type.is_filename:
                results.append(result.metadata)
                self._logger.info("Found dropbox for #%s: %s", project_id, result.metadata)
        
        if len(results) > 0 : return results
        else: raise DropboxServiceError("Couldn't find folders matching that project ID") 

        
    def _format_slug(self, project_id, title):
        '''Correctly formats  the slug for drobox'''
        self._logger.info("Creating Dropbox Slug for #%s: %s", project_id, title)
        
        title = title.lower().replace(" ", "-")
        slug = super(DropboxService, self)._format_slug(project_id, title)
        
        self._logger.info("Made Dropbox Slug for #%s: %s = %s",project_id, title, slug)
        return slug

    def _join_path(self, *args):
        '''Fixes paths to uniformly linux style'''
        fixed_path = os.path.join(*args).replace("\\","/")
        self._logger.debug("Path is= %s",fixed_path)
        return fixed_path

    def get_link_dict(self, project_id):
        '''returns a dictionary of folder: link'''
        try:
            schema = self._find_schema(project_id)
            
            response = {}
            for folder in schema['folders']:
                if folder['matches'][0]:
                    # we will lazily return the first match, i guess
                    name = ":lucid-control-dropbox: " + folder['root'].replace("/", "")
                    link = url_fix( "https://www.dropbox.com/home"+ folder['matches'][0].path_lower)
                        
                    response[name] = link

            return response
            
        except Exception as err:
            self._logger.error("Had an error getting the link dicitonary: %s", err.message)

class DropboxServiceError(service_template.ServiceException):
    pass
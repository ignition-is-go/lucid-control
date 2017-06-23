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

class DropboxService(service_template.ServiceTemplate):

    def __init__(self):

        self._logger = self._logger = self._setup_logger(to_file=True)

        self._dbx = dropbox.Dropbox(constants.DROPBOX_ACCESS_TOKEN)
        
    def create(self, project_id, title):
        '''
        Creates dropbox folder based on the schema in the ENV
        '''
        self._logger.info('Attempting to create Dropbox folder schema for #%s: %s',
            project_id, title)
        
        slug = self._format_slug('')
        try:
            folders = self._find_schema(project_id)
        except DropboxServiceError:
            # this means the folders don't exist, so carry on!
            # TODO: Skip the files that are already created, but don't fail
            schema = self._get_schema()

            responses = []
            try:
                for folder in schema['folders']:
                    self._logger.info( 'attempting to make: %s', os.path.join(folder['root'], slug))
                    response = self._dbx.files_create_folder(os.path.join(folder['root'], text))
                    self._logger.debug("Dbx Response: %s", response)
                    responses.append(response)
                    for subfolder in folder['subfolders']:
                        self._logger.info('attempting to make: %s', 
                            os.path.join(folder['root'], title, subfolder))
                        response = self._dbx.files_create_folder(os.path.join(folder['root'], text, subfolder))
                        self._logger.debug("Dbx Response: %s", response)
                        responses.append(response)

                return True
            except Exception as err:
                self._logger.error("Error while creating dropbox folders for #%s: %s",
                    project_id, err.message)
                raise err
        else:
            self._logger.error("Cannot create folders for #%s, these already exist: %s",
                project_id, folders)
            raise DropboxServiceError("Cannot create folders, these already exist: %s", 
                folders)

    def rename(self, project_id, title):
        '''
        renames dropbox folder based on the schema in the ENV
        '''
        self._logger.info('Attempting to rename Dropbox folder schema for #%s to %s',
            project_id, title)

        try:
            folders = self._find(project_id)
        except DropboxServiceError as err:
            # this means the folders don't exist, so bail!
           raise err
        else:
            responses = []
            new_slug = self._format_slug(project_id, title)
            
            for folder in folders:
                assert isinstance(folder, dropbox.files.FolderMetadata)
                path, folder_name = os.path.split(folder.path_lower)
                self._dbx.files_move(
                    folder.path_lower,
                    os.path.join(path, new_slug)
                    )

                


                    # self._logger.info( 'attempting to make: %s', os.path.join(folder['root'], text))
                    # response = self._dbx.files_create_folder(os.path.join(folder['root'], text))
                    # self._logger.debug("Dbx Response: %s", response)
                    # responses.append(response)
                    # for subfolder in folder['subfolders']:
                    #     self._logger.info('attempting to make: %s', 
                    #         os.path.join(folder['root'], title, subfolder))
                    #     response = self._dbx.files_create_folder(os.path.join(folder['root'], text, subfolder))
                    #     self._logger.debug("Dbx Response: %s", response)
                    #     responses.append(response)

        #         return True
        #     except Exception as err:
        #         self._logger.error("Error while creating dropbox folders for #%s: %s",
        #             project_id, err.message)
        #         raise err
        # else:
        #     self._logger.error("Cannot rename folders for #%s, these already exist: %s",
        #         project_id, folders)
        #     raise DropboxServiceError("Cannot rename folders, these already exist: %s", 
        #         folders) 
    
    def archive(self, project_id):
        '''Archives the folders associated with the project'''
        return True
        self._logger.info('Attempting to archive Dropbox folder schema for #%s to %s',
            project_id, title)

        try:
            folders = self._find(project_id)
        except DropboxServiceError as err:
            # this means the folders don't exist, so bail!
           raise err
        else:
            responses = []
            new_slug = self._format_slug(project_id, title)
            
            for folder in folders:
                assert isinstance(folder, dropbox.files.FolderMetadata)
                path, folder_name = os.path.split(folder.path_lower)
                self._dbx.files_move(
                    folder.path_lower,
                    os.path.join(path, new_slug)
                    )


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
                results = self._find(project_id, title=title, root=folder['root'])
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


    def _find(self, project_id, title="" ,root=""):
        '''need to refactor to find an individual file in all of dropbox!'''

        project_code = self._format_slug(project_id,title)

        search = self._dbx.files_search(root, project_code,0,100)   
        results = []
        for result in search.matches:
            if not isinstance(result, dropbox.files.SearchMatch): continue
            if result.match_type.is_filename:
                results.append(result.metadata)
                self._logger.info("Found dropbox for #%s: %s", project_id, results.metadata)
        
        if len(result) > 0 : return result
        else: raise DropboxServiceError("Couldn't find folders matching that project ID") 

        
    def _format_slug(self, project_id, title):
        '''Correctly formats  the slug for drobox'''
        self._logger.info("Creating Dropbox Slug for #%s: %s", project_id, title)
        
        title = title.lower().replace(" ", "-")
        slug = super(DropboxService, self)._format_slug(project_id, title)
        
        self._logger.info("Made Dropbox Slug for #%s: %s = %s",project_id, title, slug)
        return slug

class DropboxServiceError(service_template.ServiceException):
    pass
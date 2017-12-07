from __future__ import absolute_import, unicode_literals
import logging

from celery import shared_task
from .models import Project, ServiceConnection, TemplateProject

logger = logging.getLogger(__name__)

class ServiceAction(object):
    CREATE = 'create'
    RENAME = 'rename'
    ARCHIVE = 'archive'

@shared_task
def service_task(action, service_connection_id):
    ''' creates an element in a service, based on the service connection'''

    service_connection = ServiceConnection.objects.get(pk=service_connection_id)
    project = service_connection.project
    service = service_connection.service

    logger.info("Got service task %s on %s: %s", action, project, service)

    # defaults. this works because we only get here if service_id is blank
    service_id = ""
    connection_name = service_connection.connection_name
    try:
        if action == ServiceAction.CREATE:
            service_id, connection_name = service.create(
                project.id, 
                project.title, 
                description=service_connection.connection_name
                )
        elif action == ServiceAction.RENAME:
            service_id, connection_name = service.rename(
                service.identifier, 
                project.title, 
                description=service_connection.connection_name
                )
        elif action == ServiceAction.ARCHIVE:
            service_id, connection_name = service.archive(
                service.identifier
            )
            service_connection.is_archived = True
    except Exception as err:
        logger.error("Error with %s on %s:%s.", action, project, service, exc_info=True)

        project._message(
            "Whoops... I seem to have had a problem while trying to {action}"
            " {service} as part of {project}. \n"
            "_{error}_".format(
                action=action,
                project=project,
                service=service,
                error=err.message
            )
        )

    else:
        service_connection.identifier = service_id
        service_connection.connection_name = connection_name
        logger.info("Got id=%s from %s", service_id, service_connection.service_name)
        service_connection.save()




# create task

# import logging
# import os ,sys
# from .services import ftrack_service, xero_service, slack_service, lucid_data_service, dropbox_service, groups_service
# from .services.service_template import ServiceException
# #import all_the_functions
# import requests
# from django.conf import settings

# # setup logging
# logger = logging.getLogger(__name__)
# class Unbuffered(object):
#    def __init__(self, stream):
#        self.stream = stream
#    def write(self, data):
#        self.stream.write(data)
#        self.stream.flush()
#    def writelines(self, datas):
#        self.stream.writelines(datas)
#        self.stream.flush()
#    def __getattr__(self, attr):
#        return getattr(self.stream, attr)

# sys.stdout = Unbuffered(sys.stdout)

# logger = logging.getLogger(__name__)
# logger.setLevel(settings.LOG_LEVEL_TYPE)
# handler = logging.StreamHandler(sys.stdout)
# formatter = logging.Formatter('%(levelname)-7s| %(module)s.%(funcName)s :: %(message)s')
# handler.setFormatter(formatter)
# logger.addHandler(handler) 

# # mongo = pymongo.MongoClient(
# #     os.environ['MONGODB_URI']
# # )

# #make an instance of each service
# lucid_data = lucid_data_service.LucidDataService()
# slack = slack_service.SlackService()
# xero = xero_service.XeroService()
# ftrack = ftrack_service.FtrackService()
# google_groups = groups_service.GroupsService()
# dropbox = dropbox_service.DropboxService()

# #put these in order of desired execution
# service_collection = [
#     lucid_data,
#     slack,
#     ftrack,
#     xero,
#     groups_service,
#     dropbox
# ]

# @shared_task
# def create(title, silent=False):
#     '''
#     Runs the create methods for all services, then handles posting back to slack. 
#     Designed to run in a thread or worker process

#     #### Args:
#     - *title* (str): the title for the new project  
#     - *request* (Flask.request): the request object from the flask route call
    
#     #### Returns:
#     (bool) Success or Fail
#     '''
#     # first we need a project id, so create the lucid data entry
#     project_id = lucid_data.create(title)
    
#     successes = {}
#     failtures = {}

#     for s in service_collection:
#         try:
#             # LucidData is already done!
#             if isinstance(s, lucid_data_service.LucidDataService):
#                 continue
#             # everyone else is normal
#             else:
#                 success = s.create(project_id, title, silent=silent)

#             if success: successes[s.get_pretty_name()] = s.get_link(project_id)
#             else: failtures[s.get_pretty_name()] = "?"
        
#         except ServiceException as err:
#             failtures[s.get_pretty_name()] = err.message

#     logger.info("Service creation complete: Successes: %s \n\t\tFailtures: %s",
#                 successes, failtures)

#     #go back and redo the lucid_data one now. derp.
#     try:
#         channel_id = slack.get_id(project_id)
#         success = lucid_data.rename(project_id, title, channel_id)

#         if success: successes[lucid_data.get_pretty_name()] = lucid_data.get_link(project_id)
#         else: failtures[lucid_data.get_pretty_name()] = "?"
    
#     except ServiceException as err:
#         failtures[lucid_data.get_pretty_name()] = err.message

#     #now we make a slack message to show off what's happened
#     result_message = "*Create Project Results*\n:white_check_mark: {success}\n{fail}".format(
#         success= ", ".join(successes),
#         fail="\n".join(
#             [":heavy_exclamation_mark: {}: _{}_".format(service, error) for service, error in failtures.items()])
#     )
#     slack.post_to_project(project_id,result_message,pinned=False)

#     do_project_links(project_id, create=True)

#     return project_id


# @shared_task
# def rename(project_id, new_title):
#     '''
#     handles all the renaming of a project by id
#     '''
#     successes = []
#     failtures = {}

#     for s in service_collection:
#         try:
            
#             success = s.rename(project_id, new_title)

#             if success: successes.append(s.get_pretty_name())
#             else: failtures[s.get_pretty_name()] = "?"
        
#         except ServiceException as err:
#             failtures[s.get_pretty_name()] = err.message

#     slack_message = "*Rename Project Results*\n:white_check_mark: {success}\n{fail}".format(
#         success= ", ".join(successes),
#         fail="\n".join(
#             [":heavy_exclamation_mark: {}: _{}_".format(service, error) for service, error in failtures.items()])
#     )

#     slack.post_to_project(project_id,slack_message,pinned=False)
#     do_project_links(project_id)

#     return bool( len(failtures) > 0 )

 
# @shared_task   
# def archive(project_id, return_individual=False):
#     '''
#     handles all the archiving of a project by id
#     '''
#     successes = []
#     failtures = {}

#     for s in service_collection:
#         try:
#             # Skip slack for now so we can post results into it
#             if isinstance(s, slack_service.SlackService):
#                 continue
#             # everyone else is normal
#             else:
#                 success = s.archive(project_id)

#             if success: successes.append(s.get_pretty_name())
#             else: failtures[s.get_pretty_name()] = "?"
        
#         except ServiceException as err:
#             failtures[s.get_pretty_name()] = err.message

#     slack_message = "*Archive Project Results*\n:white_check_mark: {success}\n{fail}".format(
#         success= ", ".join(successes),
#         fail="\n".join(
#             [":heavy_exclamation_mark: {}: _{}_".format(service, error) for service, error in failtures.items()])
#     )

#     slack.post_to_project(project_id,slack_message,pinned=False)
#     # now that we've posted the results,
#     slack.archive(project_id)

#     if return_individual: return {'succeses': successes, 'failtures': failtures}
#     return bool(len(failtures)==0)


# @shared_task
# def do_project_links(project_id, create=False):

#     links = {}
#     for s in service_collection:
#         s_links = s.get_link_dict(project_id)
#         links.update(s_links)

#     link_text = "\n".join(
#             ["<{}|{}>".format(link, service) if link != "" else "" 
#                 for service, link in links.items()][::-1]
#         )
#     # for some reason, slack can't pin messages with attachments?
#     # message_attachment = [
#     #     {
#     #         "fallback": "Project links attached here",
#     #         "color": "#36a64f",
#     #         "text": link_text,
#     #         "image_url": "http://my-website.com/path/to/image.jpg",
#     #         "thumb_url": "http://example.com/path/to/thumb.png",
#     #         "footer": "Ludid Control API"
            
#     #     }
#     # ]
    

#     ref_text = "*Links for {}*".format(project_id)
    
#     if create:
#         return slack.post_to_project(project_id,ref_text+"\n"+link_text,pinned=True, unfurl_links = False)
#     else:
#         return slack.update_pinned_message(project_id,ref_text+"\n"+link_text,ref_text)

# # eof
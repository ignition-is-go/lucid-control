import logging
import os ,sys
from services import ftrack_service, xero_service, slack_service, lucid_data_service, dropbox_service, groups_service
from services.service_template import ServiceException
#import all_the_functions
import requests
import constants

# setup logging
logger = logging.getLogger(__name__)
class Unbuffered(object):
   def __init__(self, stream):
       self.stream = stream
   def write(self, data):
       self.stream.write(data)
       self.stream.flush()
   def writelines(self, datas):
       self.stream.writelines(datas)
       self.stream.flush()
   def __getattr__(self, attr):
       return getattr(self.stream, attr)

sys.stdout = Unbuffered(sys.stdout)

logger = logging.getLogger(__name__)
logger.setLevel(constants.LOG_LEVEL_TYPE)
handler = logging.StreamHandler(sys.stdout)
formatter = logging.Formatter('%(levelname)-7s| %(module)s.%(funcName)s :: %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler) 

# mongo = pymongo.MongoClient(
#     os.environ['MONGODB_URI']
# )

#make an instance of each service
lucid_data = lucid_data_service.LucidDataService()
slack = slack_service.SlackService()
xero = xero_service.XeroService()
ftrack = ftrack_service.FtrackService()
google_groups = groups_service.GroupsService()
dropbox = dropbox_service.DropboxService()

#put these in order of desired execution
service_collection = [
    lucid_data,
    slack,
    ftrack,
    xero,
    google_groups,
    dropbox
]

def create(title, silent=False):
    '''
    Runs the create methods for all services, then handles posting back to slack. 
    Designed to run in a thread or worker process

    Args:
        title (str): the title for the new project
        request (Flask.request): the request object from the flask route call
    
    Returns:
        (bool) Success or Fail
    '''
    # first we need a project id, so create the lucid data entry
    project_id = lucid_data.create(title)
    
    successes = {}
    failtures = {}

    for s in service_collection:
        try:
            # LucidData is already done!
            if isinstance(s, lucid_data_service.LucidDataService):
                continue
            # everyone else is normal
            else:
                success = s.create(project_id, title, silent=silent)

            if success: successes[s.get_pretty_name()] = s.get_link(project_id)
            else: failtures[s.get_pretty_name()] = "?"
        
        except Exception as err:
            failtures[s.get_pretty_name()] = err.message

    logger.info("Service creation complete: Successes: %s \n\t\tFailtures: %s",
                successes, failtures)

    #go back and redo the lucid_data one now. derp.
    try:
        channel_id = slack.get_id(project_id)
        success = lucid_data.rename(project_id, title, channel_id)

        if success: successes[lucid_data.get_pretty_name()] = lucid_data.get_link(project_id)
        else: failtures[lucid_data.get_pretty_name()] = "?"
    
    except ServiceException as err:
        failtures[lucid_data.get_pretty_name()] = err.message

    #now we make a slack message to show off what's happened
    result_message = "*Create Project Results*\n:white_check_mark: {success}\n{fail}".format(
        success= ", ".join(successes),
        fail="\n".join(
            [":heavy_exclamation_mark: {}: _{}_".format(service, error) for service, error in failtures.items()])
    )
    slack.post_to_project(project_id,result_message,pinned=False)

    do_project_links(project_id, create=True)

    return project_id

def rename(project_id, new_title):
    '''
    handles all the renaming of a project by id
    '''
    successes = []
    failtures = {}

    for s in service_collection:
        try:
            
            success = s.rename(project_id, new_title)

            if success: successes.append(s.get_pretty_name())
            else: failtures[s.get_pretty_name()] = "?"
        
        except ServiceException as err:
            failtures[s.get_pretty_name()] = err.message

    slack_message = "*Rename Project Results*\n:white_check_mark: {success}\n{fail}".format(
        success= ", ".join(successes),
        fail="\n".join(
            [":heavy_exclamation_mark: {}: _{}_".format(service, error) for service, error in failtures.items()])
    )

    slack.post_to_project(project_id,slack_message,pinned=False)
    do_project_links(project_id)

    return bool( len(failtures) > 0 )

    
def archive(project_id, return_individual=False):
    '''
    handles all the archiving of a project by id
    '''
    successes = []
    failtures = {}

    for s in service_collection:
        try:
            # Skip slack for now so we can post results into it
            if isinstance(s, slack_service.SlackService):
                continue
            # everyone else is normal
            else:
                success = s.archive(project_id)

            if success: successes.append(s.get_pretty_name())
            else: failtures[s.get_pretty_name()] = "?"
        
        except Exception as err:
            failtures[s.get_pretty_name()] = err.message

    slack_message = "*Archive Project Results*\n:white_check_mark: {success}\n{fail}".format(
        success= ", ".join(successes),
        fail="\n".join(
            [":heavy_exclamation_mark: {}: _{}_".format(service, error) for service, error in failtures.items()])
    )

    slack.post_to_project(project_id,slack_message,pinned=False)
    # now that we've posted the results,
    slack.archive(project_id)

    if return_individual: return {'succeses': successes, 'failtures': failtures}
    return bool(len(failtures)==0)


def do_project_links(project_id, create=False):

    links = {}
    for s in service_collection:
        s_links = s.get_link_dict(project_id)
        links.update(s_links)

    link_text = "\n".join(
            ["<{}|{}>".format(link, service) if link != "" else "" 
                for service, link in links.items()][::-1]
        )
    # for some reason, slack can't pin messages with attachments?
    # message_attachment = [
    #     {
    #         "fallback": "Project links attached here",
    #         "color": "#36a64f",
    #         "text": link_text,
    #         "image_url": "http://my-website.com/path/to/image.jpg",
    #         "thumb_url": "http://example.com/path/to/thumb.png",
    #         "footer": "Ludid Control API"
            
    #     }
    # ]
    

    ref_text = "*Links for {}*".format(project_id)
    
    if create:
        return slack.post_to_project(project_id,ref_text+"\n"+link_text,pinned=True, unfurl_links = False)
    else:
        return slack.update_pinned_message(project_id,ref_text+"\n"+link_text,ref_text)

    

# Slack input functions 
def create_from_slack(slack_message):
    logger.info("Running create_from_slack")

    if 'actions' in slack_message.keys():
        # handling actions from interactive message
        action = slack_message['actions'][0]
        logger.info("Dealing with actions %s", action)

        if action['value'] == "True":
            # the user has confirmed the action
            title = action['name']
            logger.info("User has confirmed %s", title)
            
            callback_url = slack_message['response_url']
            slack.respond_to_url(callback_url,
                "Working on creating *{}* right now for you".format(title),
                ephemeral=True)
            try:
                create(title)
            except slack_service.SlackServiceError as err:
                logger.error("Slack creation error: %s", err)

                slack.respond_to_url(callback_url,
                    text="Error creating new slack channel: *{}*".format(err.message),
                    ephemeral=True)
            
            slack.respond_to_url(callback_url,
                "Successfully created *{}* for you!".format(title),
                ephemeral=True)

        elif action['value'] == "False":
            # user canceled
            callback_url = slack_message['response_url']
            slack.respond_to_url(callback_url,
                "Ok, nevermind!",
                ephemeral=True)
                
    else:
        #send the confirmation
        url = slack_message['response_url']
        title = slack_message['text']
        slack.respond_to_url(url, ephemeral=True, attachments=[{
            "title": "Confirm Creation of {}?".format(title),
            # "fields": [
            #     {
            #         "title": "Project Name",
            #         "value": title
            #     }],
            "actions": [
                {
                    "name": title,
                    "text": "Confirm",
                    "value": "True",
                    "type": "button",
                    "style": "primary"
                },
                {
                    "name": title,
                    "text": "Cancel",
                    "value": "False",
                    "type": "button",
                    "style": "danger"
                }
            ],
            "callback_id": "create_from_slack",
            "attachment_type": "default"
        }])
    
        

def rename_from_slack(slack_message):
    '''receieves a slack channel ID and a new title, and passes to rename command the correct project_id'''
    logger.info("Running rename_from_slack")

    if 'actions' in slack_message.keys():
        # handling actions from interactive message
        action = slack_message['actions'][0]
        logger.info("Dealing with actions %s", action)

        if action['value'] == "True":
            # the user has confirmed the action
            title = action['name']
            channel = slack_message['channel']['id']
            logger.info("User has confirmed %s", title)
            
            callback_url = slack_message['response_url']
            slack.respond_to_url(callback_url,
                "Working on renaming *{}* to *{}* right now for you".format(channel, title),
                ephemeral=True)
            try:
                #first see if we can get the slack channel from the channel name    
                project_id = slack.get_project_id(slack_channel_id=channel)
            except slack_service.SlackServiceError as err:
                # couldn't find the project nubmer in the channel name
                response = ":crying_cat_face: That doesn't appear to work from here! _(the project id can't be discerned from the channel name)_"

                if callback_url is None:
                    slack.post_basic(channel, response)
                else:
                    slack.respond_to_url(callback_url,text=response)
            
            else: 
                try:
                    #try to rename
                    rename(project_id, title)
                except slack_service.SlackServiceError as err:
                    #error while renaming
                    logger.error("Slack rename error: %s", err)

                    slack.respond_to_url(callback_url,
                        text="Error creating renaming slack channel: *{}*".format(err.message),
                        ephemeral=True)
                
                else:
                    #rename success
                    slack.respond_to_url(callback_url,
                    "Successfully renamed *{}* for you!".format(title),
                    ephemeral=True)

        elif action['value'] == "False":
            # user canceled
            callback_url = slack_message['response_url']
            slack.respond_to_url(callback_url,
                "Ok, nevermind!",
                ephemeral=True)

    else:
        #send the confirmation
        url = slack_message['response_url']
        channel = slack_message['channel_name']
        title = slack_message['text']
        slack.respond_to_url(url, ephemeral=True, attachments=[{
            "title": "Confirm Renaming of {} to {}?".format(channel, title),
            # "fields": [
            #     {
            #         "title": "Project Name",
            #         "value": title
            #     }],
            "actions": [
                {
                    "name": title,
                    "text": "Confirm",
                    "value": "True",
                    "type": "button",
                    "style": "primary"
                },
                {
                    "name": title,
                    "text": "Cancel",
                    "value": "False",
                    "type": "button",
                    "style": "danger"
                }
            ],
            "callback_id": "rename_from_slack",
            "attachment_type": "default"
        }])
    

def archive_from_slack(slack_message):
    '''receieves a slack channel ID and a new title, and passes to rename command the correct project_id'''
    if 'actions' in slack_message.keys():
        # handling actions from interactive message
        action = slack_message['actions'][0]
        logger.info("Dealing with actions %s", action)

        if action['value'] == "True":
            # the user has confirmed the action
            channel = slack_message['channel']['id']
            logger.info("User has confirmed archive of %s", channel)
            
            callback_url = slack_message['response_url']
            slack.respond_to_url(callback_url,
                "Working on archiving this project right now for you",
                ephemeral=True)
            try:
                #first see if we can get the slack channel from the channel name    
                project_id = slack.get_project_id(slack_channel_id=channel)
            except slack_service.SlackServiceError as err:
                # couldn't find the project nubmer in the channel name
                response = ":crying_cat_face: That doesn't appear to work from here! _(the project id can't be discerned from the channel name)_"

                if callback_url is None:
                    slack.post_basic(channel, response)
                else:
                    slack.respond_to_url(callback_url,text=response)
            
            else: 
                try:
                    #try to archive
                    archive(project_id)
                except slack_service.SlackServiceError as err:
                    #error while renaming
                    logger.error("Slack archive error: %s", err)

                    slack.respond_to_url(callback_url,
                        text="Error creating new slack channel: *{}*".format(err.message),
                        ephemeral=True)
                

        elif action['value'] == "False":
            # user canceled
            callback_url = slack_message['response_url']
            slack.respond_to_url(callback_url,
                "Ok, nevermind!",
                ephemeral=True)
                
    else:
        #send the confirmation
        url = slack_message['response_url']
        channel = slack_message['channel_name']
        title = slack_message['text']
        slack.respond_to_url(url, ephemeral=True, attachments=[{
            "title": "Confirm archiving of all project assets?",
            # "fields": [
            #     {
            #         "title": "Project Name",
            #         "value": title
            #     }],
            "actions": [
                {
                    "name": "archive",
                    "text": "Confirm",
                    "value": "True",
                    "type": "button",
                    "style": "primary"
                },
                {
                    "name": "archive",
                    "text": "Cancel",
                    "value": "False",
                    "type": "button",
                    "style": "danger"
                }
            ],
            "callback_id": "archive_from_slack",
            "attachment_type": "default"
        }])
    
def lead_create(slack_message):
    ''' for quickly storing a lead in ftrack'''
    try:
        logger.debug("Asking slack for user info")
        user = slack.get_user(slack_message['user_id'])
        logger.debug("Sending lead to ftrack: %s, %s",
            slack_message['text'], user['profile']['email'])

        ftrack_link = ftrack.create_lead(
            slack_message['text'], user['profile']['email']
        )

        slack.respond_to_url(slack_message['response_url'],
            text=":white_check_mark: {text}: \n {url}".format(
                text=slack_message['text'],
                url=ftrack_link
            ), ephemeral=True)
    except slack_service.SlackServiceError or ftrack_service.FtrackServiceError as err:
        slack.respond_to_url(slack_message['response_url'],
            text=":warning: {}".format(err.message), ephemeral=True)

    pass
# eof
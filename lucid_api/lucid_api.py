import logging
import os
from services import ftrack_service, xero_service, slack_service, lucid_data_service, dropbox_service
from services.service_template import ServiceException
#import all_the_functions
import pymongo


logger = logging.getLogger(__name__)
#logger.setLevel(os.environ['LOG_LEVEL'])

# mongo = pymongo.MongoClient(
#     os.environ['MONGODB_URI']
# )

#make an instance of each service
lucid_data = lucid_data_service.LucidDataService()
slack = slack_service.SlackService()
xero = xero_service.XeroService()
ftrack = ftrack_service.FtrackService()
dropbox = dropbox_service.DropboxService()

#put these in order of desired execution
service_collection = [
    lucid_data,
    slack,
    ftrack,
    xero,
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
    # first we need a project id
    project_id = lucid_data.get_next_project_id()
    
    successes = {}
    failtures = {}

    for s in service_collection:
        try:
            # LucidData requires the slack channel id as well. Derp.
            if isinstance(s, lucid_data_service.LucidDataService):
                continue
            # everyone else is normal
            else:
                success = s.create(project_id, title, silent=silent)

            if success: successes[s.get_pretty_name()] = s.get_link(project_id)
            else: failtures[s.get_pretty_name()] = "?"
        
        except ServiceException as err:
            failtures[s.get_pretty_name()] = err.message

    #go back and redo the lucid_data one now. derp.
    try:
        channel_id = slack.get_id(project_id)
        success = lucid_data.create(project_id, title, channel_id)

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
        
        except ServiceException as err:
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


# Slack input functions 

def rename_from_slack(slack_channel_name, new_title):
    '''receieves a slack channel ID and a new title, and passes to rename command the correct project_id'''
    try:
        project_id = slack.get_project_id(slack_channel_name=slack_channel_name)
    except slack_service.SlackServiceError as err:
        # couldn't find the project nubmer in the channel name
        slack.post_basic(slack_channel_name, 
            ":crying_cat_face: That doesn't appear to work from here! _(the project id can't be discerned from the channel name)_")
    
    return rename(project_id, new_title)
    

def archive_from_slack(slack_channel_name):
    '''receieves a slack channel ID and a new title, and passes to rename command the correct project_id'''
    try:
        project_id = slack.get_project_id(slack_channel_name=slack_channel_name)
    except slack_service.SlackServiceError as err:
        # couldn't find the project nubmer in the channel name
        slack.post_basic(slack_channel_name, 
            ":crying_cat_face: That doesn't appear to work from here! _(the project id can't be discerned from the channel name)_")
    
    return archive(project_id)
# eof
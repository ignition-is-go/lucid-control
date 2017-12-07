# -*- coding: utf-8 -*-
'''
handles the interaction with slack
'''
from __future__ import unicode_literals
import os
import logging

import slacker

BOT_TOKEN = os.environ.get("SLACK_APP_BOT_TOKEN")
TEAM_TOKEN = os.environ.get("SLACK_APP_TEAM_TOKEN")

logger = logging.getLogger(__name__)

def send_confirmation(slack_message)
    ''' 
    send a confirmation for the command which was issued
    
    ### Params:
    - **slack_message**: a dict-like object containing the full slash command post payload

    ### Returns:
    **Nothing**
    '''
    # setup slack
    slack = slacker.Slacker(BOT_TOKEN)

    url = slack_message['response_url']
    title = slack_message.get('text', ' ')
    command = slack_message['command'][1:].title().replace("_"," ").strip()

    slack.respond_to_url(url, ephemeral=True, attachments=[{
        "title": "Confirm that you would like to {} {}?".format(command, title),
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
        "callback_id": command,
        "attachment_type": "default"
    }])

    return

def check_confirmation(slack_message):
    '''
    Checks the confirmation message and returns the command and arguments if approved

    ### Params:
    - **slack_message**: a dict-like object containing the full slash command post payload

    ### Returns:
    **(channel_id, command, args)** where **channel_id** is the channel id where the command was issued,
    **command** is the original slash command and **args** is the original argument
    '''

    if 'actions' not in slack_message.keys():
        raise AttributeError("Message does not contain an action!")
    

    # handling actions from interactive message
    action = slack_message['actions'][0]
    logger.info("Dealing with actions %s", action)

    if action['value'] == "True":
        # the user has confirmed the action
        command = slack_message['callback_id']
        arg = action['name']
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
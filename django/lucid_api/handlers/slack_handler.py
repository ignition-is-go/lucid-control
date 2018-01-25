# -*- coding: utf-8 -*-
'''
handles the interaction with slack
'''
from __future__ import unicode_literals
import os
import logging

from ..services.slack_service import Service as SlackService



logger = logging.getLogger(__name__)

def send_confirmation(slack_message, url_command):
    ''' 
    send a confirmation for the command which was issued
    
    ### Params:
    - **slack_message**: a dict-like object containing the full slash command post payload

    ### Returns:
    **Nothing**
    '''
    # setup slack
    slack = SlackService()

    url = slack_message['response_url']
    title = slack_message.get('text', 'this project')
    if not title or len(title) == 0:
        title="this project"

    slack.respond_to_url(url, ephemeral=True, attachments=[{
        "title": "Confirm that you would like to {} {}?".format(command, title),
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
        "callback_id": url_command,
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
    
    # setup slack
    slack = SlackService()
    
    # handling actions from interactive message
    action = slack_message['actions'][0]
    logger.info("Dealing with actions %s", action)

    if action['value'] == "True":
        # the user has confirmed the action
        command = slack_message['callback_id']
        arg = action['name']
        channel = slack_message['channel']['id']
        logger.info("User has confirmed %s %s on channel %s", command, arg, channel)

        callback_url = slack_message['response_url']
        slack.respond_to_url(callback_url,
            "Working on running *{} {}* right now for you".format(command, arg),
            ephemeral=True)
        
        return (channel, command, arg)

    elif action['value'] == "False":
        # user canceled
        callback_url = slack_message['response_url']
        slack.respond_to_url(callback_url,
            "Ok, nevermind!",
            ephemeral=True)

        raise UserWarning("User canceled the action")
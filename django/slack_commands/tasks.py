from __future__ import absolute_import, unicode_literals

import logging
import os
import sys

import requests
from celery import shared_task
from django.conf import settings



# # Slack input functions 
# @shared_task
# def create_from_slack(slack_message):
#     logger.info("Running create_from_slack")

#     if 'actions' in slack_message.keys():
#         # handling actions from interactive message
#         action = slack_message['actions'][0]
#         logger.info("Dealing with actions %s", action)

#         if action['value'] == "True":
#             # the user has confirmed the action
#             title = action['name']
#             logger.info("User has confirmed %s", title)
            
#             callback_url = slack_message['response_url']
#             slack.respond_to_url(callback_url,
#                 "Working on creating *{}* right now for you".format(title),
#                 ephemeral=True)
#             try:
#                 create(title)
#             except slack_service.SlackServiceError as err:
#                 logger.error("Slack creation error: %s", err)

#                 slack.respond_to_url(callback_url,
#                     text="Error creating new slack channel: *{}*".format(err.message),
#                     ephemeral=True)
            
#             slack.respond_to_url(callback_url,
#                 "Successfully created *{}* for you!".format(title),
#                 ephemeral=True)

#         elif action['value'] == "False":
#             # user canceled
#             callback_url = slack_message['response_url']
#             slack.respond_to_url(callback_url,
#                 "Ok, nevermind!",
#                 ephemeral=True)
                
#     else:
#         #send the confirmation
#         url = slack_message['response_url']
#         title = slack_message['text']
#         slack.respond_to_url(url, ephemeral=True, attachments=[{
#             "title": "Confirm Creation of {}?".format(title),
#             # "fields": [
#             #     {
#             #         "title": "Project Name",
#             #         "value": title
#             #     }],
#             "actions": [
#                 {
#                     "name": title,
#                     "text": "Confirm",
#                     "value": "True",
#                     "type": "button",
#                     "style": "primary"
#                 },
#                 {
#                     "name": title,
#                     "text": "Cancel",
#                     "value": "False",
#                     "type": "button",
#                     "style": "danger"
#                 }
#             ],
#             "callback_id": "create_from_slack",
#             "attachment_type": "default"
#         }])
    
        
# @shared_task
# def rename_from_slack(slack_message):
#     '''receieves a slack channel ID and a new title, and passes to rename command the correct project_id'''
#     logger.info("Running rename_from_slack")

#     if 'actions' in slack_message.keys():
#         # handling actions from interactive message
#         action = slack_message['actions'][0]
#         logger.info("Dealing with actions %s", action)

#         if action['value'] == "True":
#             # the user has confirmed the action
#             title = action['name']
#             channel = slack_message['channel']['id']
#             logger.info("User has confirmed %s", title)
            
#             callback_url = slack_message['response_url']
#             slack.respond_to_url(callback_url,
#                 "Working on renaming *{}* to *{}* right now for you".format(channel, title),
#                 ephemeral=True)
#             try:
#                 #first see if we can get the slack channel from the channel name    
#                 project_id = slack.get_project_id(slack_channel_id=channel)
#             except slack_service.SlackServiceError as err:
#                 # couldn't find the project nubmer in the channel name
#                 response = ":crying_cat_face: That doesn't appear to work from here! _(the project id can't be discerned from the channel name)_"

#                 if callback_url is None:
#                     slack.post_basic(channel, response)
#                 else:
#                     slack.respond_to_url(callback_url,text=response)
            
#             else: 
#                 try:
#                     #try to rename
#                     rename(project_id, title)
#                 except slack_service.SlackServiceError as err:
#                     #error while renaming
#                     logger.error("Slack rename error: %s", err)

#                     slack.respond_to_url(callback_url,
#                         text="Error creating renaming slack channel: *{}*".format(err.message),
#                         ephemeral=True)
                
#                 else:
#                     #rename success
#                     slack.respond_to_url(callback_url,
#                     "Successfully renamed *{}* for you!".format(title),
#                     ephemeral=True)

#         elif action['value'] == "False":
#             # user canceled
#             callback_url = slack_message['response_url']
#             slack.respond_to_url(callback_url,
#                 "Ok, nevermind!",
#                 ephemeral=True)

#     else:
#         #send the confirmation
#         url = slack_message['response_url']
#         channel = slack_message['channel_name']
#         title = slack_message['text']
#         slack.respond_to_url(url, ephemeral=True, attachments=[{
#             "title": "Confirm Renaming of {} to {}?".format(channel, title),
#             # "fields": [
#             #     {
#             #         "title": "Project Name",
#             #         "value": title
#             #     }],
#             "actions": [
#                 {
#                     "name": title,
#                     "text": "Confirm",
#                     "value": "True",
#                     "type": "button",
#                     "style": "primary"
#                 },
#                 {
#                     "name": title,
#                     "text": "Cancel",
#                     "value": "False",
#                     "type": "button",
#                     "style": "danger"
#                 }
#             ],
#             "callback_id": "rename_from_slack",
#             "attachment_type": "default"
#         }])
    

# @shared_task
# def archive_from_slack(slack_message):
#     '''receieves a slack channel ID and a new title, and passes to rename command the correct project_id'''
#     if 'actions' in slack_message.keys():
#         # handling actions from interactive message
#         action = slack_message['actions'][0]
#         logger.info("Dealing with actions %s", action)

#         if action['value'] == "True":
#             # the user has confirmed the action
#             channel = slack_message['channel']['id']
#             logger.info("User has confirmed archive of %s", channel)
            
#             callback_url = slack_message['response_url']
#             slack.respond_to_url(callback_url,
#                 "Working on archiving this project right now for you",
#                 ephemeral=True)
#             try:
#                 #first see if we can get the slack channel from the channel name    
#                 project_id = slack.get_project_id(slack_channel_id=channel)
#             except slack_service.SlackServiceError as err:
#                 # couldn't find the project nubmer in the channel name
#                 response = ":crying_cat_face: That doesn't appear to work from here! _(the project id can't be discerned from the channel name)_"

#                 if callback_url is None:
#                     slack.post_basic(channel, response)
#                 else:
#                     slack.respond_to_url(callback_url,text=response)
            
#             else: 
#                 try:
#                     #try to archive
#                     archive(project_id)
#                 except slack_service.SlackServiceError as err:
#                     #error while renaming
#                     logger.error("Slack archive error: %s", err)

#                     slack.respond_to_url(callback_url,
#                         text="Error creating new slack channel: *{}*".format(err.message),
#                         ephemeral=True)
                

#         elif action['value'] == "False":
#             # user canceled
#             callback_url = slack_message['response_url']
#             slack.respond_to_url(callback_url,
#                 "Ok, nevermind!",
#                 ephemeral=True)
                
#     else:
#         #send the confirmation
#         url = slack_message['response_url']
#         channel = slack_message['channel_name']
#         title = slack_message['text']
#         slack.respond_to_url(url, ephemeral=True, attachments=[{
#             "title": "Confirm archiving of all project assets?",
#             # "fields": [
#             #     {
#             #         "title": "Project Name",
#             #         "value": title
#             #     }],
#             "actions": [
#                 {
#                     "name": "archive",
#                     "text": "Confirm",
#                     "value": "True",
#                     "type": "button",
#                     "style": "primary"
#                 },
#                 {
#                     "name": "archive",
#                     "text": "Cancel",
#                     "value": "False",
#                     "type": "button",
#                     "style": "danger"
#                 }
#             ],
#             "callback_id": "archive_from_slack",
#             "attachment_type": "default"
#         }])
 

@shared_task    
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
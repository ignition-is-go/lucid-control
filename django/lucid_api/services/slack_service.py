'''
Slack Service connector for Lucid Control

K Bjordahl
6/21/19
'''

import service_template
import slacker
import requests.sessions
import os
import re
import simplejson as json
import logging

from django.apps import apps
from celery.utils.log import get_task_logger


class Service(service_template.ServiceTemplate):

    _DEFAULT_REGEX = re.compile(r'^(?P<project_id>\d{1,4})-(?P<project_title>.+)')
    _DEFAULT_FORMAT = "{project_id:d}-{connection_name}-{title}"
    _pretty_name = "Slack"

    def __init__(self, team_token=None, bot_token=None):
        '''
        Creates the necessary slacker sessions, using env vars if kwargs are not supplied
        '''
        self._logger = get_task_logger(__name__)

        self._logger.info("Created Slack Service instance")

        if bot_token is None: bot_token = os.environ.get("SLACK_APP_BOT_TOKEN")
        if team_token is None: team_token = os.environ.get("SLACK_APP_TEAM_TOKEN")

        self._slack_bot = slacker.Slacker(bot_token)
        self._slack_team = slacker.Slacker(team_token)

        # get user info for the slack bot
        self._bot_info = self._slack_bot.auth.test().body

        # self._logger = self._setup_logger(to_file=False)


    def create(self, service_connection_id):
        '''
        Handles the process of creating a new slack channel, including adding people to it

        '''
        ServiceConnection = apps.get_model("lucid_api", "ServiceConnection")
        connection = ServiceConnection.objects.get(pk=service_connection_id)
        project = connection.project

        self._logger.info(
            'Start Create Slack for %s: %s',
            connection,
            project.title
            )
            
        create_success = False
        
        slug = self._format_slug(connection)

        try: 
            # create the channel first
            create_response = self._slack_team.channels.create(name=slug)
            channel = create_response.body['channel']
            create_success = bool(create_response.body['ok'])
            
            connection.identifier = channel['id']
            if create_success:
                connection.state_message = "Created successfully!"
            else:
                connection.state_message = "Creation issue."
            connection.save()

            self._logger.debug("Slack Create Response: %s", create_response.body)

            self._logger.info("Successfully created channel for %s", slug)

        except slacker.Error as err:
            if slacker.Error.message == "is_archived":
                #we managed to try and make a channel which has the exact name as this one and is archived
                self._logger.warn("EDGE CASE: Channel %s exists and is archived", slug)
                if len(slug) == 21:
                    slug = slug[0:-1] + "_"
                else: slug += "_"

                self._logger.debug("Reattempting with slug: %s", slug)
                try:
                    create_response = self._slack_team.channels.create(name=slug)
                    channel = create_response.body['channel']
                    self._logger.info("Compromise slug %s success. Channel created", slug)
                    create_success = bool(create_response.body['ok'])

                except slacker.Error as err2:
                    self._logger.error("Another slack error: %s", err2.message)
                    raise SlackServiceError("Channel {} could not be created (is one already archived?)".format(slug))

            # whoops!
            self._logger.error("Error Creating Slack Channel for project # %s: %s", slug, err)
            raise SlackServiceError("Could not create channel for #%s, Slack API error: %s", slug, err.message)

        # invite the bot
        self._invite_bot(connection)
        connection.state_message += "\nBot invited successfully."
        connection.save()

        # invite the usergroup
        self._invite_usergroup(connection)
        connection.state_message += "\nUsers invited successfully!"
        connection.save()
                
        return True

    def rename(self, service_connection_id):
        '''
        Renames the slack channel related to *service_connection_id* based on the current value 
        of ServiceConnection.project.title

        ### Args:
        - **service_connection_id**: the primary key of the service connection this slack channel is related to

        ### Returns:
        *Nothing.* This method updates the ServiceConnection on it's own

        ### Raises:
        *services.slack_service.**SlackServiceError***: if archive fails 
        '''
        ServiceConnection = apps.get_model("lucid_api", "ServiceConnection")
        connection = ServiceConnection.objects.get(pk=service_connection_id)
        project = connection.project
        
        # generate slug based on the current project name, which has already changed, since
        # we got here via a signal on that change

        new_slug = self._format_slug(connection)
        self._logger.info('Start Rename Slack channel %s to %s',connection.connection_name, new_slug)

        try:
            rename_response = self._slack_team.channels.rename(
                channel=connection.identifier,
                name=new_slug
            )
            
            connection.state_message = "Renamed successfully!"
            connection.save()

            self._logger.info(
                "Finished Rename Slack for ProjectID %s to %s",
                project.id, 
                rename_response.body['channel']['name']
                )
            
        
        except slacker.Error as err:
            self._logger.error(
                'Could not rename #%s to %s because slacker.Error: %s',
                project_id,
                new_slug,
                err.message
                )
            raise SlackServiceError(
                "Could not rename channel for #%s, Slack API error: %s",
                project_id,
                err.message
                )
        
    def archive(self, service_connection_id):
        '''
        Archive the slack channel related to *service_connection_id*

        ### Args:
        - **service_connection_id**: the primary key of the service connection this slack channel is related to

        ### Returns:
        *Nothing.* This method updates the ServiceConnection on it's own

        ### Raises:
        *services.slack_service.**SlackServiceError***: if archive fails 
        '''
        ServiceConnection = apps.get_model("lucid_api", "ServiceConnection")
        connection = ServiceConnection.objects.get(pk=service_connection_id)
        project = connection.project
        self._logger.info('Archiving Slack for Channel %s-%s', project, connection.connection_name )

        try:
            archive_response = self._slack_team.channels.archive(
                channel=connection.identifier,
            )
            connection.state_message = "Archived successfully!"
            connection.save()

            self._logger.info("Finished Archive Slack for %s",connection)
            return archive_response.body['ok']
        
        except slacker.Error as err:
            self._logger.error(
                'Could not Archive %s because slacker.Error: %s',
                connection,
                err.message
                )
            raise SlackServiceError(
                "Could not Archive channel for %s, Slack API error: %s",
                connection,
                err.message
                )

    def unarchive(self, service_connection_id):
        '''
        Archive the slack channel related to *service_connection_id*

        ### Args:
        - **service_connection_id**: the primary key of the service connection this slack channel is related to

        ### Returns:
        *Nothing.* This method updates the ServiceConnection on it's own

        ### Raises:
        *services.slack_service.**SlackServiceError***: if archive fails 
        '''
        ServiceConnection = apps.get_model("lucid_api", "ServiceConnection")
        connection = ServiceConnection.objects.get(pk=service_connection_id)
        self._logger.info('Unarchiving Slack for Channel %s', connection.connection_name )

        try:
            archive_response = self._slack_team.channels.unarchive(
                channel=connection.identifier,
            )
            connection.state_message = "Unarchived Successfully!"
            connection.save()

            # invite the bot
            self._invite_bot(connection)
            connection.state_message += "\nBot re-invited successfully."
            connection.save()

            # invite the usergroup
            self._invite_usergroup(connection)
            connection.state_message += "\nUsers re-invited successfully!"
            connection.save()

            self._logger.info("Finished Unarchive Slack for %s",connection)
        
        except slacker.Error as err:
            self._logger.error(
                'Could not Unarchive %s because slacker.Error: %s',
                connection,
                err.message
                )
            raise SlackServiceError(
                "Could not Unarchive channel for %s, Slack API error: %s",
                connection,
                err.message
                )
                
    def message(self, channel_id, text, user=None, attachments=None, pinned=False, unfurl_links=True, action=False):
        '''
        Posts a message into the project's slack channel.

        Args:
            channel_id (int): the Slack channel ID number
            text (str): basic message text to send
            user (str): Lucid email username to send as
            attachments (dict): a slack attachment dictionary to send

        Returns:
            (bool): message success
        '''
        if user is None:
            as_user=True
            username=None
        else:
            as_user=False
            username = "{} via Lucid Control".format(user) 

        try:
            self._logger.debug("Attempting slack post: channel=%s text=%s attachments=%s",
                channel_id, text, attachments)
            
            if action:
                post_response = self._slack_bot.chat.me_message(
                    channel_id, text,
                )
            else:
                post_response = self._slack_bot.chat.post_message(
                    channel=channel_id,
                    text=text,
                    as_user=as_user,
                    username=username,
                    attachments=attachments,
                    parse=True,
                    unfurl_links=unfurl_links,
                )

            

            self._logger.debug("Posted to slack. Response: %s", post_response)
            if pinned and post_response.body['ok']:
                self._logger.debug("Attempting to pin ts=%s", post_response.body['ts'] )
                pin_response = self._slack_bot.pins.add(
                    channel=channel_id,
                    timestamp=post_response.body['ts']
                )

                pin_success = pin_response.body['ok']
            else:
                pin_success = True
        
            return bool(post_response.body['ok'] and pin_success)

        except slacker.Error as err:
            self._logger.error('Could not post to #%s because slacker.Error: %s', channel_id, err.message)
            raise SlackServiceError("Could not post to channel for #%s, Slack API error: %s", channel_id, err.message)

    def update_pinned_message(self, channel_id, text, old_text_stub, attachments=None, unfurl_links=True):
        '''Updates a pinned slack message with new text
        ### Args
        * channel_id: slack channel id
        * text: message text
        * old_text_stub: text in message to replace
        * attachments: slack api attachment array
        * unfurl_links: whether or not to unfold links into attachments (False keeps links as just linked text)
        '''
        self._logger.info("Attempting to update a pinned message starting with [%s] in project %s to %s",
            old_text_stub, channel_id, text)

        try:
            self._logger.debug("In channel %s, searching for matches to %s in pins", channel_id, old_text_stub)
            pin_list = self._slack_team.pins.list(channel_id).body
            old_ts = ""
            for pin in pin_list['items']:
                self._logger.debug("Checking %s for match", pin['message'])
                if pin['type'] == 'message' and pin['message']['text'].startswith(old_text_stub):
                    old_ts = pin['message']['ts']
                    self._logger.debug("Found matching pinned message ts=%s", old_ts)

                    update_response = self._slack_bot.chat.update(
                        channel['id'],
                        old_ts,
                        text,
                        attachments=attachments,
                        parse=True,
                        link_names=True
                    ).body

                    self._logger.info("Updated message_ts: %s successfully: %s", old_ts, update_response)
                    return update_response['ok']
                    
            if old_ts == "" :
                self._logger.error("Couldn't find message matching %s in channel %s",old_text_stub,channel)
                raise SlackServiceError("Couldn't find a pinned message matching %s", old_text_stub)
        
        except slacker.Error as err:
            self._logger.error("Had an issue with the slack API: %s", err.message)
            raise SlackServiceError("Slack API Error: %s", err.message)
                
    def post_basic(self, slack_channel_id, text):
        '''basic slack post
        slack_channel_id: 
        '''
        response = self._slack_bot.chat.post_message(
            slack_channel_id,
            text,
            parse=True,
            as_user=True
        ).body

        return response['ok']   

    def respond_to_url(self, url, text="", ephemeral=True, attachments=[]):
        '''respond to a slack action or command'''

        message = {
            'text': text,
            'attachments': attachments,
            'parse': True
        }

        if ephemeral: 
            message['response_type'] = 'ephemeral'
        
        hook = slacker.IncomingWebhook(url)

        response = hook.post(message)

        self._logger.info("Posted to %s", url)
        self._logger.info("Response: %s", response)

        return response

        if response.status_code in range(200,299):
            return True
        else:
            raise SlackServiceError("Slack returned an error: {}".format(response.contents))

    def _invite_bot(self, connection):
        try:
            #invite the bot user
            invite_bot_response = self._slack_team.channels.invite(
                channel=connection.identifier,
                user= self._bot_info['user_id']
                )
            self._logger.info("Successfully invited bot to channel for %s", connection)

        except slacker.Error as err:
            self._logger.error("Error inviting the Lucid Control Bot to the Slack Channel %s because slacker.Error: %s", connection, err)
            raise SlackServiceError("Could not invite Lucid Control Bot to channel %s, Slack API error: %s", connection, err.message)

    def _invite_usergroup(self, channel):
        '''
        invite the slack usergroup to the channel
        '''
        try:
            # try to invite the user group and the bot
            if os.environ['SLACK_INVITE_USERGROUP'] is not "" :
                invite_group_response = self._slack_team.usergroups.update(
                    usergroup=os.environ['SLACK_INVITE_USERGROUP'],
                    channel=connection.identifier,
                )
                self._logger.info("Successfully invited usergroup channel %s", connection)
                
                #check for everyone's success
                if not bool(invite_group_response.body['ok']):
                    raise SlackServiceError("Didn't successfully add everyone to the channel.")


        except slacker.Error as err:
            # failed to invite user group and bot
            self._logger.error(
                "Error inviting the proper people to the Slack Channel for project # %s because slacker.Error: %s",
                connection,
                err
                )
            raise SlackServiceError(
                "Could not invite usergroup to channel %s, Slack API error: %s",
                connection,
                err.message
                )
            
    # def get_project_id(self, slack_channel_id="", slack_channel_name=""):
    #     '''Takes a slack channel ID and returns a project_id from it'''
    #     if slack_channel_id is None and slack_channel_name is None: 
    #         self._logger.error("No name or id supplied for search")
    #         raise SlackServiceError("Must supply either channel name or ID")

    #     self._logger.info("Starting search for project ID for channel: %s", slack_channel_id)

    #     try:
    #         search = slack_channel_id if slack_channel_id is not None else "#"+slack_channel_name
    #         channel_response = self._slack_team.channels.info(search)
    #         if not channel_response.body['ok']: raise SlackServiceError("Response not OK, %s",channel_response.error)

    #     except slacker.Error or SlackServiceError as err:
    #         self._logger.error("Had an issue with accessing the team slack API: %s", err.message)
    #         raise SlackServiceError("Couldn't find the requested channel")

    #     else:
    #         self._logger.debug("Got info back: %s", channel_response)
    #         slack_channel_name = channel_response.body['channel']['name']
        
    #     self._logger.debug("Searching for slack channel name = %s", slack_channel_name)
    #     m = re.match(self._DEFAULT_REGEX, slack_channel_name)
    #     if m:
    #         project_id = int(m.group('project_id'))
    #         self._logger.info('Found a match as Project ID: %s', project_id)
    #         return project_id
    #     else:
    #         previous_names = channel_response.body['channel']['previous_names']
    #         self._logger.warn("Current name not a match, trying previous names: %s", previous_names)
    #         for old_name in previous_names:
    #             m = re.match(self._DEFAULT_REGEX, old_name)
    #             if m:
    #                 project_id = int(m.group('project_id'))
    #                 self._logger.info('Found an old name match as Project ID: %s', project_id)
    #                 return project_id
            
    #         raise SlackServiceError('Channel could not be associated with a project ID')

    
    # def get_id(self, project_id):
    #     '''
    #     Uses the project id to return a slack channel id
    #     '''
    #     try:
    #         channel = self._find(project_id)
    #     except SlackServiceError as err:
    #         raise SlackServiceError("Could not retrieve ID for the channel for #%s, because the project id could not be found", project_id)
    #     else:
    #         return channel['id']
    
    def get_link(self, project_id):
        return ""
    
    def get_user(self, user_id):
        '''gets a user's info based on slack id'''
        try:
            user = self._slack_team.users.info(user_id).body['user']
            return user
        except Exception as err:
            self._logger.error("Couldn't find user for uid %s because: %s", user_id, err.message)
            raise SlackServiceError("User not found._({})_".format(err.message))

    # def _find(self, project_id):
    #     '''
    #     Finds and returns a slack channel dictionary for the given project number
    #     '''
    #     project_id = int(project_id)
    #     self._logger.info('Searching for channel for #%s',project_id)

    #     channels = self._slack_team.channels.list(exclude_archived=True,exclude_members=True)
    
    #     self._logger.debug("Stepping through existing channels")
    #     for channel in channels.body['channels']:
    #         m = re.match(self._DEFAULT_REGEX, channel['name'])
    #         self._logger.debug("Checking channel %s", channel['name'])
    #         if m and int(m.group('project_id')) == project_id:
    #             self._logger.info('Found channel for #%s: %s',project_id,channel)
    #             return channel
        
    #     raise SlackServiceError("Couldn't find slack channel for project # %s", project_id)

    def _format_slug(self, connection):
        '''
        Makes a slack specific slug
        '''
        # m = re.match(self._DEFAULT_REGEX, title)
        # if m: title = m.group.title

        # we generate the channel slug using the project id and either the title or the description, if one is given

        slug = super(Service, self)._format_slug(connection)


        # lets use underscores instead of spaces and fix basic duplicates
        slug = slug.replace(" ", "_").replace("--","-").replace("__", "_")

        # slack has a character max, let's prep for it and fix dangling "-"
        if len(slug) > 21:
            slug = slug[0:21].strip("_-")
        
        self._logger.info("Slack Slug=%s", slug)
        return slug

class SlackServiceError(service_template.ServiceException):
    pass
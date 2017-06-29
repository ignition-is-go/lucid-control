'''
Slack Service connector for Lucid Control

K Bjordahl
6/21/19
'''

import service_template
import slacker
import constants
import requests.sessions
import os
import re
import simplejson as json


class SlackService(service_template.ServiceTemplate):

    _DEFAULT_REGEX = re.compile(r'^(?P<project_id>\d{1,4})-(?P<project_title>.+)')
    _DEFAULT_FORMAT = "{project_id:d}-{title}"
    _pretty_name = "Slack"

    def __init__(self, team_token=None, bot_token=None):
        '''
        Creates the necessary slacker sessions, using env vars if kwargs are not supplied
        '''

        if bot_token is None: bot_token = os.environ.get("SLACK_APP_BOT_TOKEN")
        if team_token is None: team_token = os.environ.get("SLACK_APP_TEAM_TOKEN")

        self._slack_bot = slacker.Slacker(bot_token)
        self._slack_team = slacker.Slacker(team_token)

        # get user info for the slack bot
        self._bot_info = self._slack_bot.auth.test().body

        self._logger = self._setup_logger(to_file=True)


    def create(self, project_id, title, silent=False):
        '''
        Handles the process of creating a new slack channel, including adding people to it
        '''
        self._logger.info('Start Create Slack for ProjectID %s: %s',project_id, title)
        create_success = False
        # first, look to see if the channel exists
        try:
            channel = self._find(project_id)
        except SlackServiceError as err:
            # this confirms the channel doesn't exist already
            slug = self._format_slug(project_id,title)

            try: 
                # create the channel first
                create_response = self._slack_team.channels.create(name=slug)
                channel = create_response.body['channel']
                create_success = bool(create_response.body['ok'])
                logger.debug("Slack Create Response: %s", create_response.body)

                self._logger.info("Successfully created channel for #%s", project_id)

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
                self._logger.error("Error Creating Slack Channel for project # %s: %s", project_id, err)
                raise SlackServiceError("Could not create channel for #%s, Slack API error: %s", project_id, err.message)

        else:
            # TODO: should we rename the channel that already exists?
            raise SlackServiceError("Couldn't create the channel for #%s, because it already exists", project_id)
        
        finally:
            #even if the channel was created already, try and invite before we throw exceptions
            
            try:

                #invite the bot user
                invite_bot_response = self._slack_team.channels.invite(
                    channel=channel['id'],
                    user= self._bot_info['user_id']
                    )
                self._logger.info("Successfully invited bot to channel for #%s", project_id)

            except slacker.Error as err:
                self._logger.error("Error inviting the Lucid Control Bot to the Slack Channel for project # %s because slacker.Error: %s", project_id, err)
                raise SlackServiceError("Could not invite Lucid Control Bot to channel for #%s, Slack API error: %s", project_id, err.message)

            try:
                if not silent and os.environ['SLACK_INVITE_USERGROUP'] is not "" :
                    invite_group_response = self._slack_team.usergroups.update(
                        usergroup=os.environ['SLACK_INVITE_USERGROUP'],
                        channels=channel['id']
                    )
                    self._logger.info("Successfully invited usergroup channel for #%s", project_id)
                    
                    #check for everyone's success
                    return bool(create_success and 
                        invite_bot_response.body['ok'] and
                        invite_group_response.body['ok'])


                else: 
                    # since we're not inviting the usergroup, don't check them for success
                    self._logger.info("Create::%s | Invite::%s", create_success, invite_bot_response.body['ok'])
                    return bool(create_success and 
                        invite_bot_response.body['ok'])

            except slacker.Error as err:
                self._logger.error("Error inviting the proper people to the Slack Channel for project # %s because slacker.Error: %s", project_id, err)
                raise SlackServiceError("Could not invite bot+usergroup to channel for #%s, Slack API error: %s", project_id, err.message)
                
            else:
                return create_response.body['ok']

    def rename(self, project_id, new_title):
        '''
        Renames a slack channel based on it's project id
        '''
        new_slug = self._format_slug(project_id,new_title)
        self._logger.info('Start Rename Slack for ProjectID %s to %s',project_id, new_slug)

        try:
            channel = self._find(project_id)
        except SlackServiceError as err:
            raise SlackServiceError("Could not rename the channel for #%s, because it could not be found", project_id)

        try:
            rename_response = self._slack_team.channels.rename(
                channel=channel['id'],
                name=new_slug
            )
            self._logger.info("Finished Rename Slack for ProjectID %s to %s",project_id, rename_response.body['channel']['name'])
            return rename_response.body['ok']
        
        except slacker.Error as err:
            self._logger.error('Could not rename #%s to %s because slacker.Error: %s',project_id,new_slug,err.message)
            raise SlackServiceError("Could not rename channel for #%s, Slack API error: %s", project_id, err.message)
        
    def archive(self, project_id):
        '''
        Archive the slack channel based on the project id
        '''
        self._logger.info('Start Archive Slack for ProjectID %s',project_id, )

        try:
            channel = self._find(project_id)
        except SlackServiceError as err:
            raise SlackServiceError("Could not Archive the channel for #%s, because it could not be found", project_id)
        else:
            try:
                archive_response = self._slack_team.channels.archive(
                    channel=channel['id'],
                )
                self._logger.info("Finished Archive Slack for ProjectID %s",project_id)
                return archive_response.body['ok']
            
            except slacker.Error as err:
                self._logger.error('Could not Archive #%s because slacker.Error: %s',project_id,err.message)
                raise SlackServiceError("Could not Archive channel for #%s, Slack API error: %s", project_id, err.message)
                
    def post_to_project(self, project_id, text, user=None, attachments=None, pinned=False, unfurl_links=True):
        '''
        Posts a message into the project's slack channel.abs

        Args:
            project_id (int): the Lucid project ID number
            text (str): basic message text to send
            user (str): Lucid email username to send as
            attachments (dict): a slack attachment dictionary to send

        Returns:
            (bool): message success
        '''
        try:
            channel = self._find(project_id)
        except SlackServiceError as err:
            raise SlackServiceError("Could not post to the channel for #%s, because it could not be found", project_id)
        
        else:
            if user is None:
                as_user=True
                username=None
            else:
                as_user=False
                username = "{} via Lucid Control".format(user) 

            try:
                self._logger.debug("Attempting slack post: channel=%s text=%s attachments=%s",
                    channel['id'], text, attachments)
                post_response = self._slack_bot.chat.post_message(
                    channel=channel['id'],
                    text=text,
                    as_user=as_user,
                    username=username,
                    attachments=attachments,
                    parse=True,
                    unfurl_links=unfurl_links
                )

                self._logger.debug("Posted to slack. Response: %s", post_response)
                if pinned and post_response.body['ok']:
                    self._logger.debug("Attempting to pin ts=%s", post_response.body['ts'] )
                    pin_response = self._slack_bot.pins.add(
                        channel=channel['id'],
                        timestamp=post_response.body['ts']
                    )

                    pin_success = pin_response.body['ok']
                else:
                    pin_success = True
            
                return bool(post_response.body['ok'] and pin_success)

            except slacker.Error as err:
                self._logger.error('Could not post to #%s because slacker.Error: %s',project_id,err.message)
                raise SlackServiceError("Could not post to channel for #%s, Slack API error: %s", project_id, err.message)

    
    def update_pinned_message(self, project_id, text, old_text_stub, attachments=None, unfurl_links=True):
        '''Updates a pinned slack message with new text'''
        self._logger.info("Attempting to update a pinned message starting with [%s] in project %s to %s",
            old_text_stub, project_id, text)

        try:
            channel = self._find(project_id)
        except SlackServiceError as err:
            self._logger.error("Couldn't find the channel for this project: %s",err.message)
            raise err

        try:
            self._logger.debug("Found channel %s, searching for matches to %s in pins", channel['id'], old_text_stub)
            pin_list = self._slack_team.pins.list(channel['id']).body
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
        '''basic slack post'''
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
            'attachments': attachments
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

    def get_project_id(self, slack_channel_id="", slack_channel_name=""):
        '''Takes a slack channel ID and returns a project_id from it'''
        if slack_channel_id is None and slack_channel_name is None: 
            self._logger.error("No name or id supplied for search")
            raise SlackServiceError("Must supply either channel name or ID")

        self._logger.info("Starting search for project ID for channel: %s", slack_channel_id)

        try:
            search = slack_channel_id if slack_channel_id is not None else slack_channel_name
            channel_response = self._slack_team.channels.info(search)
            if not channel_response.body['ok']: raise SlackServiceError("Response not OK, %s",channel_response.error)

        except slacker.Error or SlackServiceError as err:
            self._logger.error("Had an issue with accessing the team slack API: %s", err.message)
            raise SlackServiceError("Couldn't find the requested channel")

        else:
            self._logger.debug("Got info back: %s", channel_response)
            slack_channel_name = channel_response.body['channel']['name']
        
        self._logger.debug("Searching for slack channel name = %s", slack_channel_name)
        m = re.match(self._DEFAULT_REGEX, slack_channel_name)
        if m:
            project_id = int(m.group('project_id'))
            self._logger.info('Found a match as Project ID: %s', project_id)
            return project_id
        else:
            previous_names = channel_response.body['channel']['previous_names']
            self._logger.warn("Current name not a match, trying previous names: %s", previous_names)
            for old_name in previous_names:
                m = re.match(self._DEFAULT_REGEX, old_name)
                if m:
                    project_id = int(m.group('project_id'))
                    self._logger.info('Found an old name match as Project ID: %s', project_id)
                    return project_id
            
            raise SlackServiceError('Channel could not be associated with a project ID')

    def get_id(self, project_id):
        '''
        Uses the project id to return a slack channel id
        '''
        try:
            channel = self._find(project_id)
        except SlackServiceError as err:
            raise SlackServiceError("Could not retrieve ID for the channel for #%s, because the project id could not be found", project_id)
        else:
            return channel['id']
        
    
    
    def get_link(self, project_id):
        return ""
    
    def _find(self, project_id):
        '''
        Finds and returns a slack channel dictionary for the given project number
        '''
        project_id = int(project_id)
        self._logger.info('Searching for channel for #%s',project_id)

        channels = self._slack_team.channels.list(exclude_archived=True,exclude_members=True)
    
        for channel in channels.body['channels']:
            m = re.match(self._DEFAULT_REGEX, channel['name'])
            self._logger.debug("Checking channel %s", channel['name'])
            if m and int(m.group('project_id')) == project_id:
                self._logger.info('Found channel for #%s: %s',project_id,channel)
                return channel
        
        raise SlackServiceError("Couldn't find slack channel for project # %s", project_id)



    def _format_slug(self, project_id, title):
        '''
        Makes a slack specific slug
        '''
        # m = re.match(self._DEFAULT_REGEX, title)
        # if m: title = m.group.title

        slug = super(SlackService, self)._format_slug(project_id, title).lower()

        # slack has a character max, let's prep for it
        if len(slug) > 21:
            slug = slug[0:21]
            
            # check to make sure we don't dangle a '-'
            if slug[-1:] == "-":
                slug = slug[0:-1]

        # lets use underscores instead of spaces and fix basic duplicates
        slug = slug.replace(" ", "_").replace("--","-").replace("__", "_")
        

        return slug

class SlackServiceError(service_template.ServiceException):
    pass
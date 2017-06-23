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

        self._setup_logger(level='debug', to_file=True)


    def create(self, project_id, title, silent=False):
        '''
        Handles the process of creating a new slack channel, including adding people to it
        '''
        self._logger.info('Start Create Slack for ProjectID %s: %s',project_id, title)

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

                self._logger.info("Successfully created channel for #%s", project_id)

            except slacker.Error as err:
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
                    user=os.environ.get('SLACK_APP_BOT_USERID')
                    )
                self._logger.info("Successfully invited bot to channel for #%s", project_id)
                
                if not silent:
                    invite_group_response = self._slack_team.usergroups.update(
                        usergroup='S5J987J02',
                        channels=channel['id']
                    )
                    self._logger.info("Successfully invited usergroup channel for #%s", project_id)
                    
                    #check for everyone's success
                    return bool(create_response.body['ok'] and 
                        invite_bot_response.body['ok'] and
                        invite_group_response.body['ok'])

                else: 
                    # since we're not inviting the usergroup, don't check them for success
                    return bool(create_response.body['ok'] and 
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
                
    def post_to_project(self, project_id, text, user=None, attachments=None, pinned=False):
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
                post_response = self._slack_bot.chat.post_message(
                    channel=channel['id'],
                    text=text,
                    as_user=as_user,
                    username=username,
                    attachments=attachments,
                    parse=True
                )

                if pinned:
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
        self._logger.info('Searching for channel for #%s',project_id)

        channels = self._slack_team.channels.list(exclude_archived=True,exclude_members=True)
    
        for channel in channels.body['channels']:
            m = re.match(self._DEFAULT_REGEX, channel['name'])
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
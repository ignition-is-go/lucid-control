from __future__ import absolute_import, unicode_literals
import os
import json

from celery import shared_task
from .models import Profile, Workday, WorkdayOption, DayOff
from django_celery_beat.models import PeriodicTask, CrontabSchedule
from django.conf import settings

import slacker
import ftrack_api
import arrow

from celery.utils.log import get_task_logger
logger = get_task_logger(__name__)

@shared_task
def update_user_timezones():
    '''
    TODO: make this update the crontab stuff

    This task updates the celery beat crontab tasks based on the user's current
    timezone as listed in Slack
    '''
    logger.debug("Starting update_user_timezones")
    users = Profile.objects.filter(is_active=True)

    # this date will be used to decide the date
    today = arrow.utcnow()

    slack = slacker.Slacker(os.environ.get("SLACK_APP_TEAM_TOKEN"))

    for user in users:
        logger.info("Updating checkin time for %s", user)
        # for each user, get their timezone and schedule the nag task for 9am
        user_data = slack.users.info(user.slack_user)
        tz = user_data.body['user']['tz']
        # sets checkin for 9am in that timezone
        user_time = arrow.now(tz).replace(
            hour=user.start_time.hour,
            minute=user.start_time.minute,
            second=user.start_time.second)
             
        # shift post time to now
        server_time = user_time.to(settings.CELERY_TIMEZONE)

        logger.debug("Got user local time as %s, server time %s", user_time, server_time)

        if user.daily_task is None:
            # create the task and schedule
            schedule = CrontabSchedule.objects.create(
                minute=server_time.minute,
                hour=server_time.hour,
                day_of_week="*",
                day_of_month="*",
                month_of_year="*"
            )
            task = PeriodicTask.objects.create(
                name='Daily-{}'.format(user),
                task='checkin.tasks.send_workday_checkin',
                crontab=schedule,
                args=json.dumps([user.id]),
            )
            logger.debug("Creating task %s and assigning to %s", task, user)
            user.daily_task = task
            # we save at the end now
            # user.save()

        else:
            # just update the schedule
            user.daily_task.crontab.minute = server_time.minute
            user.daily_task.crontab.hour = server_time.hour
            # save the schedule
            user.daily_task.crontab.save()
            logger.debug("Updating existing task %s for %s", user.daily_task, user)
        
        user.timezone = tz
        user.save()
        
        logger.info("Updated %s's checkin time to %s (%s)",
            user, user_time, server_time)       

@shared_task(bind=True)
def send_workday_checkin(self, user_profile_id):
    '''
    Sends an individual message to ask a user to check in for today (based on Pacific TZ)
    '''

    logger.info("Sending workday checkin for user_profile_id: %s", user_profile_id)

    slacker_instance = slacker.Slacker(os.environ.get("LUCILLE_BOT_TOKEN"))
    user = Profile.objects.get(pk=user_profile_id)

    # see if the user can be accounted for today
    predetermined_response, projects = check_user_status(user)

    # create the checkin, or use the existing one
    today, created = Workday.objects.get_or_create(
        user=user,
        date=arrow.now(tz=user.timezone).date(),
        response=predetermined_response,
        )
    
    logger.debug("%s workday #%s :: %s", 
        "Created" if created else "Got",
        today.id, today)
    
    if predetermined_response is None:
        # the user couldn't be accounted for, so ask them
        send_slack_checkin.delay(
            today.id, 
            ":spiral_calendar_pad: Check in for *{today}*",
            show_options=True
        )
    else:
        # the user is accounted for, so let them know
        send_slack_response_confirmation.delay(
            today.id,
            "{response.emoji}I've marked you as *{response}* on *{today}*"
        )

    closeout_time = arrow.now().shift(hours=+12)

    close_out_workday.apply_async((today.id,), eta=closeout_time.datetime)


@shared_task(bind=True)
def handle_workday(self, data):
    '''
    Handles updating the original Interactive message to show the chosen response
    '''

    original_ts = data['message_ts']
    user = data['user']['name']
    channel = data['channel']['id']
    logger.debug("Channel: %s", channel)
    # we have to decompose the callback id we sent to slack to get the workday out of it
    _, workday_id = data['callback_id'].split("=", 1)
    today = Workday.objects.get(pk=workday_id)
    checkin_date = arrow.get(today.date).format("ddd, MMM D, YYYY")
    # get the workday option based on the slack data
    status = WorkdayOption.objects.get(pk=data['actions'][0]['value'])

    logger.info("Updating checkin %s to %s", today, status)
    logger.debug("Slack action: %s", data['actions'][0])
    logger.debug("Status is object type: %s", type(status))

    # store the response
    try:
        today.response=status
        today.slack_action_ts=data['action_ts']
        today.save()
    except Exception as e:
        logger.error("Couldn't set response!", exc_info=True)
        self.retry(exc=e)

    send_slack_response_confirmation(
        today.id,
        "{response.emoji} Thanks! I've marked you as *{response}* on *{today}*"
    )


@shared_task(bind=True)
def close_out_workday(self, workday_id):
    '''
    closes out a workday
    '''
    logger = get_task_logger(__name__)

    # get workday
    try:
        today = Workday.objects.get(pk=workday_id)
        user = today.user

    except Workday.DoesNotExist:
        logger.error("Workday #%s doesn't exist...", workday_id, exc_info=True)
        raise Workday.DoesNotExist

    else:
        logger.info("Closing out %s", today)

    # check to see if the user has responded
    if not isinstance(today.response, WorkdayOption):
        # we don't have a response

        # TODO: check with ftrack to see if the user is working on site



        # if no other option, use a day off, in this order:
        # NOTE: we have excluded flex, because the user is unreachable
        days_off = ('vacation', 'sick')

        for day_off_type in days_off:
            accrued, used = user.days(day_off_type)
            if accrued - used > 0:
                # we have this type left, use it and move on
                option = WorkdayOption.objects.filter(time_off_type=day_off_type)[0]
                break
        else:
            # TODO: figure out what to do if they don't have any days left
            # for now, they go negative on vacation days
            option = WorkdayOption.objects.filter(time_off_type='vacation')[0]

        today.response = option
        today.save()

        send_slack_response_confirmation.delay(
            today.id,
            "{response.emoji} Since you didn't respond within 12 hours, "\
            "I've marked you as *{response}* on *{today}*"
            )

    # user has checked in today.
    # let's see if they've worked over the last 7 days
    # and if so, issue them a bonus flex day
    else:
        # user has checked in today.
        # let's see if they've worked over the last 7 days
        # and if so, issue them a bonus flex day

        recent = Workday.objects.filter(
                user=today.user
            ).filter(
                date__gte=arrow.now().shift(years=-1).date()
            ).order_by('-date').select_related('response')

        # look through the days and break when we get a non-working one
        working_count = 0
        for day in recent:
            if day.response.time_off_type is None:
                # working day
                working_count+=1
            else:
                break
        
        # now modulo divide by 7. every 7th day working they get a bonus.
        if working_count % 7 == 0 and working_count > 6:
            issue_flex_day.delay(user_id=today.user.id, note="For working 7 days straight")
    
    # check to see if the user still has clickable options, if so, get rid of them
    slack = get_slack()
    try:
        today_post = slack.channels.history(
            get_user_channel_id(today.user),
            latest=today.slack_message_ts
        )
    except:
        logger.warn("Couldn't find today's post to clean up!", exc_info=True)
    else:
        if today_post.body['attachments']:
            pass




@shared_task(bind=True)
def issue_flex_day(self, note=None, user_id=None):
    '''
    issues a flex day for the current day

    ###Args:
    - **note**:optional string to add to the note field
    - **user_id**: optional, if supplied, only issue flex day to this user
    '''

    if user_id:
        users = Profile.objects.filter(pk=user_id)
    else:
        users = Profile.objects.filter(is_active=True)

    today=arrow.utcnow().date()

    slack = slacker.Slacker(os.environ.get("LUCILLE_BOT_TOKEN"))

    for user in users:
        # issue flex day
        flex_day, created = DayOff.objects.get_or_create(
            user=user,
            date=today,
            type='flex',
            amount=1,
            note="Automatically issued from 'issue_flex_day'. {}".format(note),
        )

        logger.info("Flex day added for %s on %s",user,today )
        slack.chat.post_message(
            user.slack_user,
            ":bowtie: added a *{}*. {}".format(
                flex_day,
                note
            ),
            as_user=True,
        )


@shared_task(bind=True, retry_backoff=True)
def send_slack_checkin(self, today_id, text, show_options=True):
    '''
    sends the user a checkin message via slack

    ##Args:
    -`today`: a checkin.models.Workday primary key
    -`text`: a string to supply to the slack post. {today} will be replaced with the date
    '''
    logger = get_task_logger(__name__)

    try:
        today = Workday.objects.get(pk=today_id)
    except Workday.DoesNotExist:
        logger.error("Cannot send slack checkin for workday %d, it does not exist!", today_id)
        return False

    today_str = today.date_arrow.format("ddd, MMM D, YYYY")

    slack = get_slack()

    # If the message has been posted before, wipe it clean
    if len(today.slack_message_ts) > 0:
        try:
            obj = slack.chat.update(
                channel=get_user_channel_id(today.user),
                text="_Check-in for {} was re-issued!_".format(today_str),
                attachments=[],
                ts=today.slack_message_ts,
            )
        except:
            logger.warn("Couldn't wipe old message %s", today.slack_message_ts, exc_info=True)
            pass

    # handle geting options if needed
    if show_options:
        # Get the available options, based on the workday
        option_set = WorkdayOption.objects.filter(is_active=True).order_by('sort_order')
        # format the options into an actions list for the message attachment
        actions = [option.as_json(user=today.user) for option in option_set]
    else:
        actions = None
    
    try:
        obj = slack.chat.post_message(
            channel="@{}".format(today.user.slack_user),
            text="",
            as_user=True,
            attachments=[{
                        #"pretext": "What's your status today?",
                        "text" : text.format(today=today_str),
                        "mrkdwn_in": ["text"],
                        "fallback": text.format(today=today_str),
                        "callback_id": "{callback}={id}".format(
                            callback="handle_workday",
                            id=today.id,
                            ),
                        "color": "#3AA3E3",
                        "attachment_type": "default",
                        "actions": actions
                        }]
            )

        if obj.body['ok']:
            logger.info("Slack message successful")
            today.slack_message_ts = obj.body['ts']
            today.save()
        else:
            logger.error("Slack message failed: %s", obj.body)

    except slacker.Error as e:
        logger.error("Slack API Error:", exc_info=True)
        raise self.retry(exc=e, countdown=5)


@shared_task(bind=True, retry_backoff=True)
def send_slack_response_confirmation(self, today_id, text):
    '''
    sends the user a confirmation of their response for the day.
    uses post_message if no original message has been sent

    ##Args:
    - `today`: a checkin.models.Workday primary key
    - `text`: a string to supply to the slack post. 
    -- {today} will be replaced with the date
    -- {response} is the WorkdayOption object
    '''
    logger = get_task_logger(__name__)

    try:
        today = Workday.objects.get(pk=today_id)
    except Workday.DoesNotExist:
        logger.error("Cannot send slack checkin for workday %d, it does not exist!", today_id)
        return False

    today_str = today.date_arrow.format("ddd, MMM D, YYYY")

    attachment_data = [{
        "text" : text.format(
            response=today.response, 
            today=today_str, 
            ),
        "mrkdwn_in": ["text"],
        "actions": []
    }]

    try:
        slack = get_slack()
        if today.slack_message_ts is not None:
            update_response = slack.chat.update(
                ts=today.slack_message_ts,
                text="",
                channel=get_user_channel_id(today.user),
                attachments=attachment_data
                )
            logger.debug(update_response.body)
        else:
            message_response = slack.chat.post_message(
                channel=today.user.slack_user,
                text="",
                attachments=attachment_data
            )

    except AttributeError:
        # thrown if we can't find the user im channel to update the message
        pass
    except Exception as e:
        logger.error("Couldn't update the Slack interactive message", exc_info=True)
        raise self.retry(exc=e, countdown=5)


def get_user_channel_id(user):
    ''' gets the channel id associated with a user'''
    logger=get_task_logger(__name__)
    slack = get_slack()

    # get the list of IMs and loop through it to find the user
    ims = slack.im.list().body['ims']
    for im in ims:
        if im['user'] == user.slack_user:
            channel = im['id']
            break
    else:
        logger.error("Couldn't find the IM channel for %s", user, exc_info=True)
        raise AttributeError("Couldn't find that channel")
    
    logger.debug("Channel should be %s", channel)
    return channel


def get_slack():
    '''gets a slacker instance'''
    return slacker.Slacker(settings.CHECK_IN_BOT_TOKEN)


def check_user_status(user, when=None):
    '''
    checks the user's status with the various apis

    ###Args:
    - `user`: a checkin.Profile model object
    - `when` __optional__: an Arrow time to check status for

    ##Returns:
    A tuple, consisting of (`status`, `project`) where:
    - `status`: a checkin.WorkdayOption for the user for today. `None` if the user cannot be accounted for.
    - `projects`: array of the the primary key of a the project which a user is working on, if applicable
    '''
    logger = get_task_logger(__name__)
    if logger is None:
        import logging
        logger = logging.getLogger(__name__)

    logger.info("Checking user status for %s", user)

    # figure some time stuff real quick like
    # use the time we're supplied, if given
    if isinstance(when, arrow.Arrow): 
        now = when
    else:
        now = arrow.now(tz=user.timezone)
    
    today = now.replace(hour=user.start_time.hour, minute=user.start_time.minute)
    # this is being called before the day's checkin, so count it on the day before
    if now.time() < user.start_time:
        today = today.shift(days=-1)

    # ftrack, for days on-site
    try: 
        ftrack = ftrack_api.Session()
        
        # get user
        try:
            ft_user = ftrack.query("User where email is '{}'".format(user.user.email)).one()
        except:
            logger.error("Couldn't retrieve ftrack user for %s", user, exc_info=True)
            raise IOError("Couldn't get user")
        
        # check for tasks
        try:
            query = "Task where "\
            "type.name like '%On Site%' and "\
            "assignments any (resource.id = '{id}') and "\
            "start_date <= '{next_check}' and "\
            "end_date >= '{last_check}'".format(
                id=ft_user['id'],
                next_check=today.shift(days=+1),
                last_check=today
                )

            logger.debug(query)

            tasks = ftrack.query(query)

        except:
            logger.error("Had an error querying ftrack for tasks. %s", query, exc_info=True)
            raise IOError("Query failed")

        if len(tasks) > 0:
            # user has on-site tasks today!
            try:
                option = WorkdayOption.objects.filter(time_off_type=None,name="Working")[0]
            except:
                # something has happened to the default working option!
                logger.error("Couldn't find the default working option. Is it not called Working anymore?")
                raise AttributeError("Couldn't find default working option")
            
            # let's figure out which project(s) it is
            projects = []
            try:
                for task in tasks:
                    projects.append(int(task['project']['custom_attributes']['project_id']))
            except: 
                # ok to fail for now
                pass 

            return (option, projects)
        
        else:
            logger.error("No tasks found in ftrack for %s on %s", user, today, exc_info=True)
                
    except:
        # should I do something here? just protecting to make sure all services run
        pass

    # TODO: check xero for vacation!

    # user cannot be accounted for
    return (None, [])
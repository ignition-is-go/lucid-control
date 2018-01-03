from __future__ import absolute_import, unicode_literals
import os
import json

from celery import shared_task
from .models import Profile, Workday, WorkdayOption, DayOff
from django_celery_beat.models import PeriodicTask, CrontabSchedule
from django.conf import settings

import slacker
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
        user_time = arrow.now(tz).replace(hour=9,minute=0,second=0)
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
        else:
            # just update the schedule
            user.daily_task.crontab.minute = server_time.minute
            user.daily_task.crontab.hour = server_time.hour
            logger.debug("Updating existing task %s for %s", user.daily_task, user)
        
        # Be sure to save!    
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

    # create the checkin, or use the existing one
    today, created = Workday.objects.get_or_create(
        user=user,
        date=arrow.now().date(),
    )
    logger.debug("%s workday #%s :: %s", 
        "Created" if created else "Got",
        today.id, today)
    
    today_str = today.date_arrow.format("ddd, MMM D, YYYY")
    checkin_str = today.date_arrow.format("MM/DD/YY")

    # If the message has been posted before, wipe it clean
    if len(today.slack_message_ts) > 0:
        try:
            ims = slacker_instance.im.list().body['ims']
            for im in ims:
                if im['user'] == user.slack_user:
                    channel = im['id']
                    break
            
            logger.debug("Channel should be %s", channel)
            obj = slacker_instance.chat.update(
                channel=channel,
                text="_Check-in for {} was re-issued!_".format(today_str),
                attachments=[],
                ts=today.slack_message_ts,
            )
        except:
            logger.warn("Couldn't wipe old message %s", today.slack_message_ts, exc_info=True)
            pass

    # TODO: Update this to show the running totals for each type of day off
    option_set = WorkdayOption.objects.filter(is_active=True).order_by('sort_order')
    
    actions = [option.as_json(user=user) for option in option_set]
    try:
        obj = slacker_instance.chat.post_message(
            channel="@{}".format(user.slack_user),
            text="",
            as_user=True,
            attachments=[{
                        #"pretext": "What's your status today?",
                        "text" : ":spiral_calendar_pad: Check in for *{}*".format(today_str),
                        "mrkdwn_in": ["text"],
                        "fallback": "Time to check in!",
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
            today.is_posted = True
            today.slack_message_ts = obj.body['ts']
            today.save()
        else:
            logger.error("Slack message failed: %s", obj.body)

        #TODO: setup end-of-day closeout task here
        closeout_time = arrow.now().shift(hours=+16)


    except slacker.Error as e:
        logger.error("Slack API Error:", exc_info=True)
        raise self.retry(exc=e, countdown=5)

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

    #  THIS IS FOR THE OLD WorkdayResponse method... 
    #  TODO: remove once safe
    # # store the response in the DB
    # response, created = WorkdayResponse.objects.get_or_create(
    #     workday=today,
    #     response=WorkdayOption.objects.get(pk=status_id),
    #     slack_action_ts=data['action_ts']
    # )
    # logger.debug("%s response #%s :: %s", 
    #     "Created" if created else "Got",
    #     response.id, response)

    # store the response
    try:
        today.response=status
        today.slack_action_ts=data['action_ts']
        today.save()
    except Exception as e:
        logger.error("Couldn't set response!", exc_info=True)
        self.retry(exc=e)

    slack = slacker.Slacker(os.environ.get('LUCILLE_BOT_TOKEN'))

    try:
        update_response = slack.chat.update(
            ts=original_ts,
            text="",
            channel=channel,
            attachments=[{
                "text" : "{icon} Thanks! I've marked you as *{status}* on *{date}*".format(
                    status=status, 
                    date=checkin_date, 
                    icon=status.emoji
                    ),
                "mrkdwn_in": ["text"],
                "actions": []
            }]
            )
        logger.debug(update_response.body)

    except:
        logger.error("Couldn't update the Slack interactive message", exc_info=True)
    
 
    pass

# TODO: closeout day task
@shared_task(bind=True)
def close_out_workday(self, workday_id):
    pass
    
@shared_task(bind=True)
def issue_flex_day(self):
    '''
    issues a flex day for the current day
    '''

    users = Profile.objects.filter(is_active=True)
    arrow.utcnow().date()

    for user in users:
        # issue flex day
        flex_day = DayOff.objects.get_or_create(
            user=user,
            date=today,
            type='flex',
            amount=1,
            note="Automatically issued from 'issue_flex_day'",
        )
        logger.info("Flex day added for %s on %s",user,today )


from __future__ import absolute_import, unicode_literals
import os

from celery import shared_task
from .models import Profile, Workday, WorkdayOption, WorkdayResponse
from django.conf import settings

import slacker
import arrow

from celery.utils.log import get_task_logger
import logging
logger = logging.getLogger(__name__)
# logger = get_task_logger(__name__)

@shared_task
def setup_daily_checkin():
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
        # for each user, get their timezone and schedule the nag task for 9am
        user_data = slack.users.info(user.slack_user)
        tz = user_data.body['user']['tz']
        # sets checkin for 9am
        post_time = arrow.now(tz).replace(hour=9,minute=0,second=0)
        # If the post time is in the past, jump it a day ahead
        if post_time < arrow.now(tz):
            post_time.shift(days=+1)
        # create a new checkin and save it
        checkin = Workday(
            user=user,
            date=today.date,
            scheduled=post_time,
        )
        checkin.save()

        # set up celery task
        send_nag_message.apply_async((checkin.id), eta=post_time.datetime)

@shared_task()
def send_workday_checkin( user_profile_id ):
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

    # TODO: Update this to show the running totals for each type of day off
    option_set = WorkdayOption.objects.filter(is_active=True)
    
    actions = [option.as_json() for option in option_set]
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
            today.is_posted = True
            today.slack_message_ts = obj.body['ts']
            today.save()

        #TODO: setup end-of-day closeout task here
        closeout_time = arrow.now().shift(hours=+16)


    except slacker.Error as e:
        raise e

@shared_task
def handle_workday( data ):
    '''
    Handles updating the original Interactive message to show the chosen response
    '''

    original_ts = data['message_ts']
    user = data['user']['name']
    channel = data['channel']['id']
    # we have to decompose the callback id we sent to slack to get the workday out of it
    _, workday_id = data['callback_id'].split("=", 1)
    today = Workday.objects.get(pk=workday_id)
    checkin_date = arrow.get(today.date).format("ddd, MMM D, YYYY")
    status_id = data['actions'][0]['value']

    logger.debug("Updating message for checkin #%s", workday_id)

    # store the response in the DB
    response, created = WorkdayResponse.objects.get_or_create(
        workday=today,
        response=WorkdayOption.objects.get(pk=status_id),
        slack_action_ts=data['action_ts']
    )
    logger.debug("%s response #%s :: %s", 
        "Created" if created else "Got",
        response.id, response)

    slack = slacker.Slacker(os.environ.get('LUCILLE_BOT_TOKEN'))

    try:
        update_response = slack.chat.update(
            ts=original_ts,
            text="",
            channel=channel,
            attachments=[{
                "text" : "{icon} Thanks! I've marked you as *{status}* on *{date}*".format(
                    status=response.response, 
                    date=checkin_date, 
                    icon=response.response.emoji
                    ),
                "mrkdwn_in": ["text"],
                "actions": []
            }]
            )
        logger.debug(update_response.body)

    except:
        logger.error("Couldn't update the Slack interactive message", exc_info=True)
    
 
    pass

@shared_task
def test():
    logger.info("Testing! %s", arrow.utcnow().isoformat())
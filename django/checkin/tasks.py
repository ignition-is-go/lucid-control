from __future__ import absolute_import, unicode_literals
import logging
import os

from celery import shared_task
from .models import Profile, Workday, WorkdayOption
from django.conf import settings

import slacker
import arrow

@shared_task
def setup_daily_checkin():
    '''
    Checks in with all users based on their TZ in slack.

    Should be triggered at 00:00:00 UTC daily
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
def send_nag_message( workday_id ):
    '''
    Sends an individual message to ask a user to check in for today (based on Pacific TZ)
    '''

    slacker_instance = slacker.Slacker(os.environ.get("LUCILLE_BOT_TOKEN"))
    workday = Workday.objects.get(workday_id)

    # because Lucille lives in CA, where Lucid is HQ'd
    today = arrow.get(workday.date)

    today_str = today.format("ddd, MMM D, YYYY")
    checkin_str = today.format("MM/DD/YY")
    actions = [option.as_json() for option 
        in WorkdayOption.objects.filter(is_active=True)]

    try:
        obj = slacker_instance.chat.post_message(
            channel="@{}".format(workday.user.slack_user),
            text="",
            as_user=True,
            attachments=[{
                        #"pretext": "What's your status today?",
                        "text" : ":spiral_calendar_pad: Check in for *{}*".format(today_str),
                        "mrkdwn_in": ["text"],
                        "fallback": "Time to check in!",
                        "callback_id": workday.id,
                        "color": "#3AA3E3",
                        "attachment_type": "default",
                        "actions": actions
                        }]
            )

        if obj.body['ok']:
            workday.is_posted = True
            workday.save()

        #TODO: setup end-of-day closeout task here

    except slacker.Error as e:
        raise e

def update_initial_message( data ):
    '''
    Handles updating the original Interactive message to show the chosen response
    '''

    original_ts = data['message_ts']
    user = data['user']['name']
    channel = data['channel']['id']
    workday_id = data['callback_id']
    workday = Workday.objects.get(workday_id)
    checkin_date = workday.date.format
    status = data['actions'][0]['value']
    
    logger = logging.getLogger(__name__)
    logger.debug("Updating message for checkin #%s", workday_id)

    #TODO: get data from updated workday entry

    update_response = get_slack().chat.update(
        ts=original_ts,
        text="",
        channel=channel,
        attachments=[{
            "text" : "{2} Thanks! I've marked you as *{0}* on *{1}*".format(
                status, 
                checkin_date, 
                icon
                ),
            "mrkdwn_in": ["text"],
            "actions": []
        }]
        )

    print(update_response.body)
    sys.stdout.flush()

    return update_response.successful

        
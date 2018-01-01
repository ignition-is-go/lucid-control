# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import arrow

from django.db import models
from django.contrib.auth.models import User
from django_celery_beat.models import CrontabSchedule

class Profile(models.Model):
    '''
    Profile for a Checkin user. Has a one-to-one relationship to a django.contrib.auth User
    '''
    
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        blank=False,
    )
    slack_user = models.CharField(
        max_length=50,
        blank=False,
    )
    # daily_checkin_beat = models.ForeignKey(
    #     CrontabSchedule,
    #     on_delete=models.CASCADE,
    #     related_name="profile",
    #     verbose_name="Daily Check-in Schedule",
    #     blank=True
    # )
    is_active = models.BooleanField(
        default=True,
    )

    def __str__(self):
        return self.user.get_username()

    class Meta():
        verbose_name="Checkin User"
        verbose_name_plural="Users"


class WorkdayOption(models.Model):
    '''
    Possible options for responses to the workday query
    '''
    name = models.CharField(
        verbose_name="Name",
        max_length=200,
        blank=False,
        unique=True,
    )
    emoji = models.CharField(
        verbose_name="Emoji Text",
        max_length=200,
        blank=True,
    )
    flex_adjustment = models.FloatField(
        verbose_name="Flex Days Adjustment",
        help_text='Whether to add or remove flex days. Decimal days are acceptable'
    )
    vacation_penalty = models.BooleanField(
        verbose_name="Vacation Day Penalty",
        help_text='Whether or not this day reduces vacation days',
        default=False,
    )
    sick_penalty = models.BooleanField(
        verbose_name="Sick Day Penalty",
        help_text='Whether or not this day reduces sick days',
        default=False,
    )
    is_active = models.BooleanField(
        default = True
    )
    require_confirmation = models.BooleanField(
        help_text="Whether or not to require the user to confirm",
        default=False,
    )
    confirmation_text = models.CharField(
        help_text="Only applied when confirmation is required",
        default="",
        blank=True,
        max_length=500,
    )
    style = models.CharField(
        choices=[
            ("primary","Primary"),
            ("default","Default"),
            ("danger", "Danger")
        ],
        default="default",
        max_length=50,
    )
    sort_order = models.IntegerField(
        verbose_name="Display order for options. Must be unique.",
        unique=True,
        blank=False,
    )

    def as_json(self):
        '''
        Return a JSON version of the option for use in slack messages
        '''
        action_button = dict(
            name="workday_option",
            text="{} {}".format(self.emoji, self.name),
            type="button",
            value=self.id,
            style=self.style,
        )

        if self.require_confirmation:
            action_button['confirm']=dict(
                title="Are you sure?",
                text=self.confirmation_text,
                ok_text="Yes",
                dismiss_text="No"
            )

        return action_button
    
    def __str__(self):
        return self.name


class Workday(models.Model):
    ''' 
    A record of a checkin for a single user for a day.

    This is created when the checkin is posted
    '''

    date = models.DateField(
        verbose_name="Checkin Date",
        blank=False,
    )
    user = models.ForeignKey(
        Profile,
        on_delete=None,
        blank=False,
        related_name="workdays",
    )
    scheduled = models.DateTimeField(
        help_text="timestamp from when the checkin was scheduled",
        auto_now_add=True,
        blank=False,
    )
    is_posted = models.BooleanField(
        help_text="Whether the check-in has been sent",
        default=False,
    )
    last_action = models.DateTimeField(
        verbose_name="Last Action Time",
        auto_now=True,
        blank=False,
    )
    slack_message_ts = models.CharField(
        max_length=100,
        verbose_name="Slack message_ts",
        default="",
        blank=True,
        null=True
    )

    def __str__(self):
        return "{date} - {name}".format(
            date = self.date,
            name = self.user.user.get_username()
        )

    @property
    def date_arrow(self):
        ''' return the date as arrow object'''
        return arrow.get(self.date)
    

class WorkdayResponse(models.Model):
    '''
    a user response to the workday checkin
    '''
    workday = models.ForeignKey(
        Workday,
        on_delete=None,
        blank=False,
        related_name="responses",
    )
    response = models.ForeignKey(
        WorkdayOption,
        on_delete=models.CASCADE,
        related_name="response",
        blank=True,
        limit_choices_to={'is_active': True}
    )
    timestamp = models.DateTimeField(
        auto_now_add=True,
    )
    slack_action_ts = models.CharField(
        max_length=100,
        verbose_name="Slack action_ts",
        # unique=True,
        default=""
    )

    class Meta():
        verbose_name="Option"
        verbose_name_plural="Options"

# class EffortLog(models.Model):
#     '''
#     A log of effort on a project
#     '''

#     user = models.ForeignKey(
#         Profile,
#         on_delete=None,
#     )
#     project = models.ForeignKey(
#         Project,
#         on_delete=models.CASCADE,
#     )


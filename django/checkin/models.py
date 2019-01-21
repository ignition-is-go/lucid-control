# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import datetime

import arrow
import math

import pytz

from django.db import models
from django.db.models import Sum, Count, Q, Case, When
from django.contrib.auth.models import User
from django_celery_beat.models import PeriodicTask

TIME_OFF_TYPES = [
    ('vacation', 'Vacation'),
    ('sick', 'Sick'),
    ('flex', 'Flex')
]

TIMEZONES = [(tz, tz) for tz in pytz.all_timezones]

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
        verbose_name="Slack Member ID",
        help_text="This should be something like <strong>U1ADJNUJX</strong>"
    )
    timezone = models.CharField(
        max_length=200,
        blank=True,
        choices=TIMEZONES,
    )
    start_time = models.TimeField(
        verbose_name="Workday Start Time",
        blank=False,
        default=datetime.time(9,1)
    )
    daily_task = models.OneToOneField(
        PeriodicTask,
        on_delete=models.CASCADE,
        related_name="profile",
        verbose_name="Daily Check-in Schedule",
        blank=True,
        null=True
    )
    is_active = models.BooleanField(
        default=True,
    )

    def __str__(self):
        return self.user.get_username()

    def days(self, time_off_type):
        '''
        determines the number of available days of *time_off_type*
        '''
        filters = dict(
            # flex days are good for 1 year
            flex=Q(date__gte=arrow.now().shift(years=-1).date()),
            # vacation never expires
            vacation=Q(date__lte=arrow.now().date()),
            # sick days reset each year
            sick=Q(date__year=arrow.now().year)
        )
        

        try:
            # get time off used
            # use filter per type
            used = self.workdays.filter(filters[time_off_type]).aggregate(
                days=Sum(Case(
                    When( response__time_off_type=time_off_type, then='response__time_off_adjustment' ),
                    output_field=models.IntegerField()
                ))
            )['days']
            # check for none value
            if used is None: raise ValueError
        except:
            used = 0

        try:
            # get accrued time off
            # use filter per type
            accrued = self.accrued_days_off.filter(filters[time_off_type]).aggregate(
                days=Sum(Case(
                    When( type=time_off_type, then='amount' ),
                    output_field=models.IntegerField()
                ))
            )['days']
            # check for none value
            if accrued is None: raise ValueError
        except:
            accrued = 0

        return accrued, used
        

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
    time_off_type = models.CharField(
        max_length=100,
        choices=TIME_OFF_TYPES,
        blank=True,
        null=True,
    )
    time_off_adjustment = models.FloatField(
        blank=False,
        default=0,
    )
    is_active = models.BooleanField(
        default = True,
        verbose_name = "Enabled"
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

    def as_json(self, user=None):
        '''
        Return a JSON version of the option for use in slack messages

        ###Args:
        - **user**: a *Profile*-model object. If supplied, buttons will show the 
        number of available days of each type, and be hidden if no days remain.
        '''
        action_button = dict(
            name="workday_option",
            text="{} {}".format(self.emoji, self.name),
            type="button",
            value=self.id,
            style=self.style,
        )

        # check to see if we've supplied a user, and if so, display the number
        # of available days of this type. Return None if there are no days left.
        if user is not None and self.time_off_type is not None:
            accrued, used = user.days(self.time_off_type)
            remaining = accrued - used
            if remaining <= 0:
                # no more of this day type available, return no JSON option
                return None
            else:
                action_button['text'] += " ({:0.0f})".format(
                    math.floor(accrued-used)
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
        on_delete=models.CASCADE,
        blank=False,
        related_name="workdays",
    )
    scheduled = models.DateTimeField(
        help_text="timestamp from when the checkin was scheduled",
        auto_now_add=True,
        blank=False,
    )
    # is_posted = models.BooleanField(
    #     help_text="Whether the check-in has been sent",
    #     default=False,
    # )
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
    response = models.ForeignKey(
        WorkdayOption,
        on_delete=None,
        related_name="response",
        blank=True,
        null=True,
        limit_choices_to={'is_active': True},
        verbose_name="Status",
    )
    slack_action_ts = models.CharField(
        max_length=100,
        verbose_name="Slack action_ts",
        # unique=True,
        default=""
    ) 

    def __str__(self):
        return "{date} - {name} - {status}".format(
            date = self.date,
            name = self.user,
            status = self.current_status
        )

    @property
    def date_arrow(self):
        ''' return the date as arrow object'''
        return arrow.get(self.date)
    
    @property
    def current_status(self):
        return self.response or "(waiting...)"

class DayOff(models.Model):
    '''
    An individually accrued amount of time off for a user
    '''

    user = models.ForeignKey(
        Profile,
        on_delete=models.CASCADE,
        related_name="accrued_days_off",
    )
    date = models.DateField(
        verbose_name="Issue Date",
        blank=False,
    )
    type = models.CharField(
        max_length=100,
        choices=TIME_OFF_TYPES
    )
    amount = models.FloatField(
        verbose_name="Days",
        help_text='Number of days to add. Decimals OK',
        blank=False,
    )
    note = models.TextField(
        blank=True,
        null=True,
    )
    timestamp = models.DateTimeField(
        auto_now=True
    )

    def __str__(self):
        return "{s.type} day for {s.user} on {s.date}".format(s=self)

    class Meta():
        verbose_name = "Day Off"
        verbose_name_plural = "Days Off"

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


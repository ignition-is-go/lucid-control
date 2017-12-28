# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models
from django.contrib.auth.models import User

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
    is_active = models.BooleanField(
        default=True,
    )

    class Meta():
        verbose_name="Checkin User",
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
        return dict(
            name=workday_option,
            text="{} {}".format(self.emoji, self.name),
            type="button",
            value=self.id,
            style=self.style,
            confirm=dict(
                title="Are you sure?",
                text=self.confirmation_text,
                ok_text="Yes",
                dismiss_text="No"
            ) if self.require_confirmation else None
        )
    
    def __str__(self):
        return self.name
    

class Workday(models.Model):
    ''' 
    A record of a checkin for a single user for a day.

    This is created when the checkin is scheduled
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
    checkin_time = models.DateTimeField(
        help_text="When the checkin is scheduled for",
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
    response = models.ForeignKey(
        WorkdayOption,
        on_delete=models.CASCADE,
        related_name="response",
        blank=True,
        limit_choices_to={'is_active': True}
    )


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


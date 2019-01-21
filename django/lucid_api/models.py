# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db.models.signals import post_init
from django.dispatch import receiver
from django.db import models

import services

# get the list of services
SERVICE_LIST = []
for service_class in services.__all__:
    # get the class instance to get the pretty name
    service = getattr(services, service_class)
    SERVICE_LIST.append((service_class, service.Service._pretty_name))

SERVICE_LIST = sorted(SERVICE_LIST)


class DirtyFieldsMixin(object):
    def __init__(self, *args, **kwargs):
        super(DirtyFieldsMixin, self).__init__(*args, **kwargs)
        self._original_state = self._as_dict()

    def _as_dict(self):
        return dict([(f.name, getattr(self, f.name)) for f in self._meta.local_fields if not f.rel])

    def get_dirty_fields(self):
        new_state = self._as_dict()
        return dict([(key, value) for key, value in self._original_state.iteritems() if value != new_state[key]])

# Create your models here.


class ProjectType(models.Model):
    '''Lucid project types'''
    character_code = models.CharField(
        verbose_name="Character Code",
        max_length=1,
        blank=False,
        primary_key=True
    )
    description = models.CharField(
        verbose_name="Project Type",
        max_length=500,
        blank=False
    )
    # is_default = models.BooleanField(
    #     verbose_name="Default Project Type",
    #     help_text="If checked, this will be used as the type when creating new projects via the api",
    #     default=False,
    #     blank=False,
    # )

    @property
    def chr(self):
        return str(self.character_code).upper()

    def __str__(self):
        return self.description

    class Meta:
        verbose_name = "Project Type"


class Project(DirtyFieldsMixin, models.Model):
    ''' Lucid project '''

    type_code = models.ForeignKey(
        ProjectType,
        verbose_name="Type",
        default="P",
    )
    title = models.CharField(
        verbose_name="Project Title",
        max_length=200
    )
    is_archived = models.BooleanField(
        verbose_name="Archived",
        help_text="This will automatically archive all connected services.",
        default=False
    )

    def __str__(self):
        return "{self.type_code.chr}-{self.id:04d} {self.title}".format(self=self)

    def message(self, message, **kwargs):
        '''used by celery tasks to send messages to the project.

        '''

        for service in self.services.filter(is_messenger=True):
            service.send(message, **kwargs)

    class Meta:
        verbose_name = "Project"
        verbose_name_plural = "Projects"


class ServiceConnection(DirtyFieldsMixin, models.Model):
    '''service connections to a project'''

    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name="services"
    )
    service_name = models.CharField(
        max_length=200,
        verbose_name="Service Name",
        choices=SERVICE_LIST,
        blank=False
    )
    # connection name is only necessary to disambiguate multiple connections to
    # the same service per project (slack? i dunno, maybe I'm planning too hard)
    connection_name = models.CharField(
        max_length=200,
        blank=True,
        default="",
        help_text="Used by some connection types to differentiate multiple connections"
    )
    identifier = models.CharField(
        max_length=500,
        blank=True,
        help_text="If left blank, a new connection to this service will be created."
    )
    is_messenger = models.BooleanField(
        verbose_name="Messenger Channel",
        help_text="If checked, this channel will receive all Lucid Control messages",
        default=False,
    )
    is_archived = models.BooleanField(
        verbose_name="Archived",
        default=False
    )
    state_message = models.CharField(
        verbose_name="Status",
        max_length=1000,
        default="",
        blank=True,
    )

    @property
    def service(self):
        ''' returns an instance of the service class that this connection represents'''
        service_module = getattr(services, self.service_name)
        return service_module.Service()

    def send(self, message, **kwargs):
        ''' send a message using this service.

        *If this is not a messenger service, raise AttributeError*
        '''

        if not self.is_messenger:
            raise AttributeError("Not a messenger connection")

        response = self.service.message(self.identifier, message, **kwargs)

        return response

    def __str__(self):
        return ":{s.service_name}::{s.project} - {s.connection_name}".format(s=self)

    class Meta():
        verbose_name = "Service Connection"


class TemplateProject(models.Model):
    ''' This model is used to define the template that is used to create new projects'''

    objects = models.Manager()

    def __str__(self):
        return "Template Project"


class TemplateServiceConnection(models.Model):
    template = models.ForeignKey(
        TemplateProject,
        on_delete=models.CASCADE,
        related_name="services",
    )
    service_name = models.CharField(
        max_length=200,
        verbose_name="Service Name",
        choices=SERVICE_LIST
    )

    # connection name is only necessary to disambiguate multiple connections to
    # the same service per project (slack? i dunno, maybe I'm planning too hard)
    connection_name = models.CharField(
        max_length=200,
        blank=True,
        default=""
    )
    is_messenger = models.BooleanField(
        default=False,
        verbose_name="Messenger Channel",
    )

    objects = models.Manager()

    class Meta():
        verbose_name = "Template Project"
        verbose_name_plural = "Template Project"

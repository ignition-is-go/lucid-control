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

    @property
    def chr(self):
        return str(self.character_code).upper()

    def __str__(self):
        return self.description

    class Meta:
        verbose_name="Project Type"


class Project(models.Model):
    ''' Lucid project '''
    type_code = models.ForeignKey(
        ProjectType,
        verbose_name="Type"
    )
    title = models.CharField(
        verbose_name="Project Title", 
        max_length=200
    )
    is_archived = models.BooleanField(
        verbose_name="Archived",
        default=False
    )

    def __str__(self):
        return "{self.type_code.chr}-{self.id:04d} {self.title}".format(self=self)

    def _message(self, message, ephemeral=False):
        '''used by celery tasks to send messages to the project.

        TODO: implement as slack message
        '''
        pass

    class Meta:
        verbose_name="Project"
        verbose_name_plural="Projects"


class ServiceConnection(models.Model):
    '''service connections to a project'''

    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name="services"
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

    @property
    def service(self):
        ''' returns an instance of the service class that this connection represents'''
        service_module = getattr(services, self.service_name)
        return service_module.Service()

    def __str__(self):
        return "{s.service_name}::{s.connection_name}".format(s=self)

    class Meta():
        verbose_name="Service Connection"

class TemplateProject(models.Model):
    ''' This model is used to define the template that is used to create new projects'''
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

    class Meta():
        verbose_name ="Template Project"
        verbose_name_plural = "Template Project"
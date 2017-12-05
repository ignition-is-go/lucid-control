# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models

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
        ProjectType
    )
    title = models.CharField(
        verbose_name="Project Title", 
        max_length=200
    )

    def __str__(self):
        return "{self.type_code.chr}-{self.id:04d} {self.title}".format(self=self)

    class Meta:
        verbose_name="Project"
        verbose_name_plural="Projects"


@receiver(models.signals.post_init, sender=Project)
def execute_after_save(sender, instance, *args, **kwargs):
    if created:
        # do the create tasks here!
        pass
 
class ServiceConnection(models.Model):
    '''service connections to a project'''

    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name="services",
    )

    service_list = (
        ("slack", "Slack"),
        ("ftrack", "ftrack"),
        ("dropbox", "dropbox"),
        ("xero", "Xero"),
        ("googlegroups", "Google groups"),
    )

    service_name = models.CharField(
        max_length=200,
        verbose_name="Service Name",
        choices=service_list
    )

    # connection name is only necessary to disambiguate multiple connections to 
    # the same service per project (slack? i dunno, maybe I'm planning too hard)
    connection_name = models.CharField(
        max_length=200,
        blank=True,
        default=""
    )

    identifier = models.CharField(
        max_length=500,
        blank=False
    )



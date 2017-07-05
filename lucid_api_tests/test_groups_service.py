'''
Google Group Service Tests

Tests for the Google Groups Service connector on Lucid Control (Lucid API)

JT
6/25/17
'''

import basic_test_data
from basic_test_data import sample_project_data
import pytest
import simplejson as json
import os
from lucid_api.services.groups_service import GroupsService, GroupsServiceError

@pytest.fixture(scope='session')
def groups():
    '''
    Build Google Groups Service for testing
    '''

    return GroupsService()

@pytest.fixture(scope='module')
def sample_project(request, sample_project_data, groups):
    ''' 
    Setup a sample project and erase it
    '''

    yield sample_project_data

    try:
        groups.archive(sample_project_data['project_id'])
    except:
        pass

@pytest.fixture(scope='module')
def prebuilt_sample_project(request, sample_project, groups):
    '''
    Build a sample project
    '''

    assert groups.create(
            sample_project['project_id'],
            sample_project['project_title'],
            invite=False)
    yield sample_project

def test_groups_prevent_duplicate_create(groups, prebuilt_sample_project):
    with pytest.raises(GroupsServiceError):
        groups.create(
            prebuilt_sample_project['project_id'],
            prebuilt_sample_project['project_title'])

def test_groups_rename(groups, prebuilt_sample_project):
    assert groups.rename(
        prebuilt_sample_project['project_id'], "-RENAME")

def test_groups_archive(groups, prebuilt_sample_project):
    assert groups.archive(prebuilt_sample_project['project_id'])



@pytest.fixture(scope='session')
def test_create_group
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
    yield sample_project_data


@pytest.fixture(scope='session')
def test_create_group
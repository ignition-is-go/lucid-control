'''
Lucid API Tests
tests for the combined usage of the Service connectors on Lucid Control (Lucid API)

K Bjordahl
6/20/17
'''

import basic_test_data
from basic_test_data import sample_project_data
from slack_service_test import slack
from FtrackService_test import ftrack
from xero_service_test import xero
import pytest
import simplejson as json
import os

import lucid_api

cleanup_ids = []

@pytest.fixture(scope='module')
def sample_project(request, sample_project_data):
    yield sample_project_data

    #need to archive here!
    cleanup_ids = getattr(request.module, 'cleanup_ids', [])
    print cleanup_ids
    for id in cleanup_ids:
        lucid_api.archive(id)


def test_create_with_teardown( sample_project, slack, ftrack, xero ):

    title = sample_project['project_title']
    project_id = lucid_api.create(title, silent=True)
    
    try:
        assert slack._find(project_id)['name'] == slack._format_slug(project_id, title)
        assert xero._find(project_id)['Name'] == xero._format_slug(project_id, title)
        assert ftrack._find(project_id)['full_name'] == ftrack._format_slug(project_id, title)
    finally:
        assert lucid_api.archive(project_id)
